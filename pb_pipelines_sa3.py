
"""
Scientific analysis pipelines for pbsmrtpipe/SMRT Link, not including HGAP.
"""

import logging
import functools
import sys

from pbcommand.models.common import to_pipeline_ns
from pbcommand.models import FileTypes

from pbsmrtpipe.core import register_pipeline
from pbsmrtpipe.constants import ENTRY_PREFIX
from pbsmrtpipe.pb_pipelines.pb_pipeline_constants import Constants, Tags, to_entry


VERSION = "0.1"
log = logging.getLogger(__name__)

# pylint: disable=E0102

def sa3_register(relative_id, display_name, version, tags=(), task_options=None):
    pipeline_id = to_pipeline_ns(relative_id)
    return register_pipeline(pipeline_id, display_name, version, tags=tags, task_options=task_options)


def _core_align(subread_ds, reference_ds):
    # Call blasr/pbalign
    b3 = [(subread_ds, "pbalign.tasks.pbalign:0"),
          (reference_ds, "pbalign.tasks.pbalign:1")]
    return b3


def _core_align_plus(subread_ds, reference_ds):
    bs = _core_align(subread_ds, reference_ds)

    b4 = [("pbalign.tasks.pbalign:0", "pbreports.tasks.mapping_stats:0")]

    b5 = [("pbalign.tasks.pbalign:0", "pbalign.tasks.consolidate_alignments:0")]

    return bs + b4 + b5


def _core_gc(alignment_ds, reference_ds):
    b1 = [(reference_ds, "genomic_consensus.tasks.variantcaller:1"),
          (alignment_ds, "genomic_consensus.tasks.variantcaller:0")]
    b2 = [("genomic_consensus.tasks.variantcaller:0", "genomic_consensus.tasks.gff2bed:0")]
    return b1 + b2


def _core_gc_plus(alignment_ds, reference_ds):
    """
    Returns a list of core bindings
    """

    # Need to have a better model to avoid copy any paste. This is defined in the
    # fat resquencing pipeline.
    # Summarize Coverage
    b1 = _core_gc(alignment_ds, reference_ds)

    b2 = [(alignment_ds, "pbreports.tasks.summarize_coverage:0"),
          (reference_ds, "pbreports.tasks.summarize_coverage:1")]

    b3 = [(reference_ds, "pbreports.tasks.coverage_report:0"),
          ("pbreports.tasks.summarize_coverage:0",
           "pbreports.tasks.coverage_report:1")]

    b4 = [("pbreports.tasks.summarize_coverage:0", "genomic_consensus.tasks.summarize_consensus:0"),
          ("genomic_consensus.tasks.variantcaller:0", "genomic_consensus.tasks.summarize_consensus:1")]

    # Consensus Reports - variants
    b5 = [(reference_ds, "pbreports.tasks.variants_report:0"),
          ("genomic_consensus.tasks.summarize_consensus:0", "pbreports.tasks.variants_report:1"),
          ("genomic_consensus.tasks.variantcaller:0", "pbreports.tasks.variants_report:2")]

    # Consensus Reports - top variants
    b6 = [("genomic_consensus.tasks.variantcaller:0", "pbreports.tasks.top_variants:0"),
          (reference_ds, "pbreports.tasks.top_variants:1")]

    return b1 + b2 + b3 + b4 + b5 + b6


@sa3_register("sa3_fetch", "RS Movie to Subread DataSet", "0.1.0", tags=(Tags.CONVERTER, ))
def sa3_fetch():
    """
    Convert RS movie metadata XML to Subread DataSet XML
    """

    # convert to RS dataset
    b1 = [(Constants.ENTRY_RS_MOVIE_XML, "pbscala.tasks.rs_movie_to_ds_rtc:0")]

    b2 = [("pbscala.tasks.rs_movie_to_ds_rtc:0", "pbcoretools.tasks.h5_subreads_to_subread:0")]

    return b1 + b2


@sa3_register("sa3_align", "RS movie Align", "0.1.0", tags=(Tags.MAP, ))
def sa3_align():
    """
    Perform mapping to reference sequence, starting from RS movie XML
    """
    # convert to RS dataset
    b1 = [(Constants.ENTRY_RS_MOVIE_XML, "pbscala.tasks.rs_movie_to_ds_rtc:0")]

    # h5 dataset to subread dataset via bax2bam
    b2 = [("pbscala.tasks.rs_movie_to_ds_rtc:0", "pbcoretools.tasks.h5_subreads_to_subread:0")]

    bxs = _core_align_plus("pbcoretools.tasks.h5_subreads_to_subread:0", Constants.ENTRY_DS_REF)

    return b1 + b2 + bxs


@sa3_register("sa3_resequencing", "RS movie Resequencing", "0.1.0", tags=Tags.RESEQ)
def sa3_resequencing():
    """
    Resequencing Pipeline - Blasr mapping and Genomic Consensus, starting from
    RS movie XML
    """
    return _core_gc("pbsmrtpipe.pipelines.sa3_align:pbalign.tasks.pbalign:0", Constants.ENTRY_DS_REF)


@sa3_register("sa3_hdfsubread_to_subread", "Convert RS to BAM", "0.1.0", tags=(Tags.CONVERTER, ))
def hdf_subread_converter():
    """
    Import HdfSubreadSet (bax.h5 basecalling files) to SubreadSet (.bam files)
    """
    b2 = [(Constants.ENTRY_DS_HDF, "pbcoretools.tasks.h5_subreads_to_subread:0")]

    return b2


@sa3_register("sa3_ds_align", "SubreadSet Mapping", "0.1.0", tags=(Tags.MAP, Tags.INTERNAL))
def ds_align():
    """
    Perform Blasr mapping to reference sequence
    """
    return _core_align_plus(Constants.ENTRY_DS_SUBREAD, Constants.ENTRY_DS_REF)


UNROLLED_TASK_OPTIONS = {
    "pbalign.task_options.no_split_subreads": True,
    "pbalign.task_options.hit_policy": "leftmost",
    "pbalign.task_options.concordant": False,
    "pbalign.task_options.algorithm_options": "--bestn 1 --forwardOnly --fastMaxInterval --maxAnchorsPerPosition 30000 --minPctIdentity 60"
}

# XXX this is identical to sa3_ds_align but with modified task options
@sa3_register("sa3_ds_align_unrolled", "Unrolled Template SubreadSet Mapping",
              "0.1.0", tags=(Tags.MAP, Tags.INTERNAL),
              task_options=UNROLLED_TASK_OPTIONS)
def ds_align_unrolled():
    """
    Perform Blasr mapping to reference sequence, using entire unsplit
    polymerase reads implicit in the SubreadSet (with scraps).
    """
    return _core_align_plus(Constants.ENTRY_DS_SUBREAD, Constants.ENTRY_DS_REF)


RESEQUENCING_TASK_OPTIONS = {
    "genomic_consensus.task_options.diploid": False,
    "genomic_consensus.task_options.algorithm": "best",
    "pbalign.task_options.algorithm_options": "--minMatch 12 --bestn 10 --minPctSimilarity 70.0 --refineConcordantAlignments",
    "pbalign.task_options.concordant": True,
}


@sa3_register("sa3_ds_genomic_consensus", "Genomic Consensus", "0.1.0",
              tags=(Tags.CONSENSUS, Tags.INTERNAL),
            task_options=RESEQUENCING_TASK_OPTIONS)
def ds_genomic_consenus():
    """
    Run Genomic Consensus, starting from an existing AlignmentSet
    """
    return _core_gc_plus(Constants.ENTRY_DS_ALIGN, Constants.ENTRY_DS_REF)


@sa3_register("sa3_ds_resequencing", "Basic Resequencing", "0.1.0",
              tags=Tags.RESEQ_INTERNAL, task_options=RESEQUENCING_TASK_OPTIONS)
def ds_resequencing():
    """
    Core Resequencing Pipeline - Blasr mapping and Genomic Consensus
    """
    return _core_gc("pbsmrtpipe.pipelines.sa3_ds_align:pbalign.tasks.pbalign:0", Constants.ENTRY_DS_REF)


_OPTIONS = RESEQUENCING_TASK_OPTIONS.copy()


@sa3_register("sa3_ds_resequencing_fat",
              "Resequencing", "0.1.0",
              task_options=_OPTIONS, tags=Tags.RESEQ_RPT)
def ds_fat_resequencing(subreads=Constants.ENTRY_DS_SUBREAD):
    """
    Full Resequencing Pipeline - Blasr mapping and Genomic Consensus, plus
    additional reports
    """

    filt = [(subreads, "pbcoretools.tasks.filterdataset:0")]
    aln = _core_align_plus("pbcoretools.tasks.filterdataset:0", Constants.ENTRY_DS_REF)
    return filt + aln + _core_gc_plus("pbalign.tasks.pbalign:0", Constants.ENTRY_DS_REF)


def _core_mod_detection(alignment_ds, reference_ds):
    bs = []
    _add = bs.append

    # AlignmentSet, ReferenceSet
    _add((alignment_ds, "kinetics_tools.tasks.ipd_summary:0"))
    _add((reference_ds, 'kinetics_tools.tasks.ipd_summary:1'))

    _add(('kinetics_tools.tasks.ipd_summary:2', 'pbreports.tasks.modifications_report:0'))
    return bs


BASEMODS_TASK_OPTIONS = dict(RESEQUENCING_TASK_OPTIONS)
BASEMODS_TASK_OPTIONS["genomic_consensus.task_options.algorithm"] = "best"
BASEMODS_TASK_OPTIONS["kinetics_tools.task_options.pvalue"] = 0.001

@sa3_register("ds_modification_detection",
                   'Base Modification Detection', "0.1.0",
                   tags=(Tags.MOD_DET, ), task_options=BASEMODS_TASK_OPTIONS)
def rs_modification_detection_1():
    """
    Base Modification Analysis Pipeline - performs resequencing workflow
    and detects methylated bases from kinetic data
    """
    b1 = _core_align_plus(Constants.ENTRY_DS_SUBREAD, Constants.ENTRY_DS_REF)
    b2 = _core_mod_detection("pbalign.tasks.pbalign:0", Constants.ENTRY_DS_REF)
    b3 = [("pbalign.tasks.pbalign:0", "pbreports.tasks.summarize_coverage:0"),
          (Constants.ENTRY_DS_REF, "pbreports.tasks.summarize_coverage:1")]

    b4 = [
        # basemods.gff
        ("kinetics_tools.tasks.ipd_summary:0", "kinetics_tools.tasks.summarize_modifications:0"),
        # alignment_summary.gff
        ("pbreports.tasks.summarize_coverage:0", "kinetics_tools.tasks.summarize_modifications:1")
    ]
    return b1 + b2 + b3 + b4


def _core_motif_analysis(ipd_gff, reference_ds):
    bs = []
    x = bs.append
    # Find Motifs. AlignmentSet, ReferenceSet
    x((ipd_gff, 'motif_maker.tasks.find_motifs:0'))  # basemods GFF
    x((reference_ds, 'motif_maker.tasks.find_motifs:1'))

    # Make Motifs GFF: ipdSummary GFF, ipdSummary CSV, MotifMaker CSV, REF
    x((ipd_gff, 'motif_maker.tasks.reprocess:0'))  # GFF
    # XXX this is not currently used
    #_add(('pbsmrtpipe.pipelines.ds_modification_detection:kinetics_tools.tasks.ipd_summary:1', 'motif_maker.tasks.reprocess:1')) # CSV
    x(('motif_maker.tasks.find_motifs:0', 'motif_maker.tasks.reprocess:1'))  # motifs GFF
    x((reference_ds, 'motif_maker.tasks.reprocess:2'))

    # MK Note. Pat did something odd here that I can't remember the specifics
    x(('motif_maker.tasks.reprocess:0', 'pbreports.tasks.motifs_report:0'))
    x(('motif_maker.tasks.find_motifs:0', 'pbreports.tasks.motifs_report:1'))

    return bs


@sa3_register("ds_modification_motif_analysis", 'Base Modification and Motif Analysis', "0.1.0",
              tags=(Tags.MOTIF, ), task_options=BASEMODS_TASK_OPTIONS)
def rs_modification_and_motif_analysis_1():
    """
    Modification and Motif Analysis Pipeline - performs resequencing workflow,
    detects methylated bases from kinetic data, and identifies consensus
    nucleotide motifs
    """
    return _core_motif_analysis(
        'pbsmrtpipe.pipelines.ds_modification_detection:kinetics_tools.tasks.ipd_summary:0', Constants.ENTRY_DS_REF)


@sa3_register("pb_modification_detection", 'PacBio Internal Modification Analysis', "0.1.0",
              tags=(Tags.RPT, Tags.MOD_DET, Tags.INTERNAL ),
              task_options={"kinetics_tools.task_options.pvalue":0.001})
def pb_modification_analysis_1():
    """
    Internal base modification analysis pipeline, starting from an existing
    AlignmentSet
    """
    return _core_mod_detection(Constants.ENTRY_DS_ALIGN, Constants.ENTRY_DS_REF)


@sa3_register("pb_modification_motif_analysis", 'PacBio Internal Modification and Motif Analysis', "0.1.0",
              tags=Tags.RESEQ_MOTIF, task_options={"kinetics_tools.task_options.pvalue": 0.001})
def pb_modification_and_motif_analysis_1():
    """
    Internal base modification and motif analysis pipeline, starting from an
    existing AlignmentSet
    """
    return _core_motif_analysis('pbsmrtpipe.pipelines.pb_modification_detection:kinetics_tools.tasks.ipd_summary:0',
                                Constants.ENTRY_DS_REF)


def _core_sat(reseq_pipeline):
    # AlignmentSet, GFF, mapping Report
    x = [("{p}:pbalign.tasks.pbalign:0".format(p=reseq_pipeline),
          "pbreports.tasks.sat_report:0"),
         ("{p}:pbreports.tasks.variants_report:0".format(p=reseq_pipeline),
          "pbreports.tasks.sat_report:1"),
         ("{p}:pbreports.tasks.mapping_stats:0".format(p=reseq_pipeline),
          "pbreports.tasks.sat_report:2")]
    return x


SAT_TASK_OPTIONS = RESEQUENCING_TASK_OPTIONS.copy()
SAT_TASK_OPTIONS["genomic_consensus.task_options.algorithm"] = "plurality"

@sa3_register("sa3_sat", 'Site Acceptance Test (SAT)', "0.1.0",
              tags=(Tags.MAP, Tags.CONSENSUS, Tags.RPT, Tags.SAT),
              task_options=SAT_TASK_OPTIONS)
def rs_site_acceptance_test_1():
    """
    Site Acceptance Test - lambda genome resequencing used to validate new
    PacBio installations
    """
    return _core_sat("pbsmrtpipe.pipelines.sa3_ds_resequencing_fat")


def _core_export_fastx(subread_ds):
    b1 = [(subread_ds, "pbcoretools.tasks.bam2fasta_archive:0")]
    b2 = [(subread_ds, "pbcoretools.tasks.bam2fastq_archive:0")]
    return b1 + b2


def _core_export_fastx_ccs(ccs_ds):
    b1 = [(ccs_ds, "pbcoretools.tasks.bam2fasta_ccs:0")]
    b2 = [(ccs_ds, "pbcoretools.tasks.bam2fastq_ccs:0")]
    return b1 + b2


def _core_laa(subread_ds):
    # Call ccs
    b3 = [(subread_ds, "pblaa.tasks.laa:0")]
    return b3


def _core_laa_plus(subread_ds):
    laa = _core_laa(subread_ds)
    split_fastq = [
        ("pblaa.tasks.laa:0", "pbcoretools.tasks.split_laa_fastq:0"),
        ("pblaa.tasks.laa:1", "pbcoretools.tasks.split_laa_fastq:1")
    ]
    consensus_report = [
        ("pblaa.tasks.laa:2", "pbreports.tasks.amplicon_analysis_consensus:0")
    ]
    inputs_report = [
        ("pblaa.tasks.laa:3", "pbreports.tasks.amplicon_analysis_input:0")
    ]
    return laa + split_fastq + consensus_report + inputs_report


@sa3_register("sa3_ds_laa", "Long Amplicon Analysis (LAA)", "0.1.0", tags=(Tags.LAA, ))
def ds_laa():
    """
    Basic Long Amplicon Analysis (LAA) pipeline, starting from subreads.
    """
    subreadset = Constants.ENTRY_DS_SUBREAD
    return _core_laa_plus(Constants.ENTRY_DS_SUBREAD)


def _core_barcode(subreads=Constants.ENTRY_DS_SUBREAD):
    return [
        (subreads, "barcoding.tasks.lima:0"),
        (Constants.ENTRY_DS_BARCODE, "barcoding.tasks.lima:1"),
        ("barcoding.tasks.lima:0", "pbcoretools.tasks.update_barcoded_sample_metadata:0"),
        (subreads, "pbcoretools.tasks.update_barcoded_sample_metadata:1"),
        (Constants.ENTRY_DS_BARCODE, "pbcoretools.tasks.update_barcoded_sample_metadata:2"),
        ("pbcoretools.tasks.update_barcoded_sample_metadata:0", "pbreports.tasks.barcode_report:0"),
        (subreads, "pbreports.tasks.barcode_report:1"),
        (Constants.ENTRY_DS_BARCODE, "pbreports.tasks.barcode_report:2")
    ]


def _core_barcode_old(subreads=Constants.ENTRY_DS_SUBREAD):
    return [
        (subreads, "pbcoretools.tasks.bam2bam_barcode:0"),
        (Constants.ENTRY_DS_BARCODE, "pbcoretools.tasks.bam2bam_barcode:1")
    ]


@sa3_register("sa3_ds_barcode", "Barcoding", "0.2.0",
              tags=(Tags.BARCODE,Tags.INTERNAL))
def ds_barcode():
    """
    SubreadSet barcoding pipeline
    """
    return _core_barcode_old()


BARCODING_OPTIONS = {
    "lima.task_options.library_same_tc": True,
    "lima.task_options.peek_guess_tc": True
}
@sa3_register("sa3_ds_barcode2", "Demultiplex Barcodes (Auto)", "0.1.0",
              tags=(Tags.BARCODE,Tags.INTERNAL), task_options=BARCODING_OPTIONS)
def ds_barcode2():
    """
    SubreadSet barcoding pipeline
    """
    return _core_barcode()


@sa3_register("sa3_ds_barcode2_manual", "Demultiplex Barcodes", "0.1.0",
              tags=(Tags.BARCODE,), task_options=BARCODING_OPTIONS)
def ds_barcode2():
    """
    SubreadSet barcoding pipeline
    """
    b1 = [
        (Constants.ENTRY_DS_SUBREAD, "pbcoretools.tasks.reparent_subreads:0")
    ]
    return b1 + _core_barcode("pbcoretools.tasks.reparent_subreads:0")


def _barcode2_filter():
    b1 = _core_barcode()
    b2 = [
        ("pbcoretools.tasks.update_barcoded_sample_metadata:0", "pbcoretools.tasks.datastore_to_subreads:0"),
        ("pbcoretools.tasks.datastore_to_subreads:0", "pbcoretools.tasks.filterdataset:0")
    ]
    return b1 + b2


@sa3_register("pb_barcode2_filter", "Barcoding plus dataset filtering", "0.1.0",
              tags=(Tags.BARCODE,Tags.DEV), task_options=BARCODING_OPTIONS)
def pb_barcode2_filter():
    return _barcode2_filter()


@sa3_register("pb_barcode2_laa", "LAA with Barcoding (Internal Testing)", "0.2.0", tags=(Tags.BARCODE, Tags.LAA, Tags.INTERNAL), task_options=BARCODING_OPTIONS)
def ds_barcode2_laa():
    """
    Combined barcoding and long amplicon analysis pipeline
    """
    b1  = _core_barcode()
    b2 = [("pbcoretools.tasks.update_barcoded_sample_metadata:0", "pbcoretools.tasks.datastore_to_subreads:0")]
    subreadset = "pbcoretools.tasks.datastore_to_subreads:0"
    b3 = _core_laa_plus(subreadset)
    return b1 + b2 + b3


# global defaults for CCS jobs
CCS_TASK_OPTIONS = {
  "pbccs.task_options.min_read_score": 0.65,
}

def _core_ccs(subread_ds):
    # Call ccs
    b3 = [(subread_ds, "pbccs.tasks.ccs:0")]
    # CCS report
    b4 = [("pbccs.tasks.ccs:0", "pbreports.tasks.ccs_report:0")]
    b5 = _core_export_fastx_ccs("pbccs.tasks.ccs:0")
    return b3 + b4 + b5


@sa3_register("sa3_ds_ccs", "Circular Consensus Sequences (CCS)", "0.2.0", tags=(Tags.CCS, ), task_options=CCS_TASK_OPTIONS)
def ds_ccs():
    """
    Basic ConsensusRead (CCS) pipeline, starting from subreads.
    """
    b1 = [(Constants.ENTRY_DS_SUBREAD, "pbcoretools.tasks.filterdataset:0")]
    return b1 + _core_ccs("pbcoretools.tasks.filterdataset:0")


CCS_BARCODE_OPTIONS = dict(CCS_TASK_OPTIONS)
CCS_BARCODE_OPTIONS.update(BARCODING_OPTIONS)
@sa3_register("pb_barcode2_ccs", "CCS with Barcoding (Internal Testing)", "0.2.0", tags=(Tags.BARCODE, Tags.CCS, Tags.INTERNAL), task_options=CCS_BARCODE_OPTIONS)
def pb_barcode2_ccs():
    """
    Combined barcoding and CCS pipeline
    """
    return _core_ccs("pbsmrtpipe.pipelines.pb_barcode2_filter:pbcoretools.tasks.filterdataset:0")


def _core_ccs_align(ccs_ds):
    # pbalign w/CCS input
    b3 = [(ccs_ds, "pbalign.tasks.pbalign_ccs:0"),
          (Constants.ENTRY_DS_REF, "pbalign.tasks.pbalign_ccs:1")]
    # mapping_stats_report (CCS version)
    b4 = [("pbalign.tasks.pbalign_ccs:0",
           "pbreports.tasks.mapping_stats_ccs:0")]
    return b3+b4


@sa3_register("sa3_ds_ccs_align", "CCS Mapping", "0.2.0", tags=(Tags.CCS, Tags.MAP, ), task_options=CCS_TASK_OPTIONS)
def ds_align_ccs():
    """
    ConsensusRead (CCS) + Mapping pipeline, starting from subreads.
    """
    b1 = _core_ccs_align("pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0")
    b2 = [("pbalign.tasks.pbalign_ccs:0",
           "pbreports.tasks.summarize_coverage_ccs:0"),
          (Constants.ENTRY_DS_REF, "pbreports.tasks.summarize_coverage_ccs:1")]
    b3 = [(Constants.ENTRY_DS_REF, "pbreports.tasks.coverage_report:0"),
          ("pbreports.tasks.summarize_coverage_ccs:0",
           "pbreports.tasks.coverage_report:1")]
    return b1 + b2 + b3


@sa3_register("pb_ccs_align", "Internal Consensus Read Mapping", "0.1.0", tags=(Tags.MAP, Tags.CCS, Tags.INTERNAL))
def pb_align_ccs():
    """
    Internal ConsensusRead (CCS) alignment pipeline, starting from an existing
    ConsensusReadSet.
    """
    return _core_ccs_align(Constants.ENTRY_DS_CCS)


def _core_isoseq_classify(ccs_ds):
    b3 = [ # classify all CCS reads - CHUNKED (ContigSet scatter)
        (ccs_ds, "pbtranscript.tasks.classify:0")
    ]
    b4 = [ # pbreports isoseq_classify
        ("pbtranscript.tasks.classify:1", "pbreports.tasks.isoseq_classify:0"),
        ("pbtranscript.tasks.classify:3", "pbreports.tasks.isoseq_classify:1")
    ]
    return b3 + b4


def _core_isoseq_cluster(ccs_ds, flnc_ds, nfl_ds):
    """Deprecated, replaced by _core_isoseq_cluster_chunk_by_bins."""
    b5 = [ # cluster reads and get consensus isoforms
        # full-length, non-chimeric transcripts
        (flnc_ds, "pbtranscript.tasks.cluster:0"),
        # non-full-length transcripts
        (nfl_ds, "pbtranscript.tasks.cluster:1"),
        (ccs_ds, "pbtranscript.tasks.cluster:2"),
        (Constants.ENTRY_DS_SUBREAD, "pbtranscript.tasks.cluster:3")
    ]
    b6 = [ # ice_partial to map non-full-lenth reads to consensus isoforms
        # non-full-length transcripts
        (nfl_ds, "pbtranscript.tasks.ice_partial:0"),
        # draft consensus isoforms
        ("pbtranscript.tasks.cluster:0", "pbtranscript.tasks.ice_partial:1"),
        (ccs_ds, "pbtranscript.tasks.ice_partial:2"),
    ]
    b7 = [
        (Constants.ENTRY_DS_SUBREAD, "pbtranscript.tasks.ice_quiver:0"),
        ("pbtranscript.tasks.cluster:0", "pbtranscript.tasks.ice_quiver:1"),
        ("pbtranscript.tasks.cluster:3", "pbtranscript.tasks.ice_quiver:2"),
        ("pbtranscript.tasks.ice_partial:0", "pbtranscript.tasks.ice_quiver:3")
    ]
    b8 = [
        (Constants.ENTRY_DS_SUBREAD, "pbtranscript.tasks.ice_quiver_postprocess:0"),
        ("pbtranscript.tasks.cluster:0", "pbtranscript.tasks.ice_quiver_postprocess:1"),
        ("pbtranscript.tasks.cluster:3", "pbtranscript.tasks.ice_quiver_postprocess:2"),
        ("pbtranscript.tasks.ice_partial:0", "pbtranscript.tasks.ice_quiver_postprocess:3"),
        ("pbtranscript.tasks.ice_quiver:0", "pbtranscript.tasks.ice_quiver_postprocess:4")
    ]
    b9 = [ # pbreports isoseq_cluster
        # draft consensus isoforms
        ("pbtranscript.tasks.cluster:0", "pbreports.tasks.isoseq_cluster:0"),
        # json report
        ("pbtranscript.tasks.ice_quiver_postprocess:0", "pbreports.tasks.isoseq_cluster:1"),
    ]

    return b5 + b6 + b7 + b8 + b9

def _core_isoseq_cluster_chunk_by_bins(subreads_ds, ccs_ds, flnc_ds, nfl_ds):
    """Core isoseq cluster pipeline, further chunk ICE, ice_partial, ice_polish
       by (read sizes or primer) bins, deprecated _core_isoseq_cluster."""
    # separate_flnc
    b1 = [(flnc_ds, "pbtranscript.tasks.separate_flnc:0")]

    # create chunks for ICE, ice_partial, ice_polish
    b2 = [("pbtranscript.tasks.separate_flnc:0", "pbtranscript.tasks.create_chunks:0"),
          (nfl_ds, "pbtranscript.tasks.create_chunks:1")]

    # run ICE cluster on bins
    b3 = [("pbtranscript.tasks.create_chunks:0", "pbtranscript.tasks.cluster_bins:0"),
          (ccs_ds, "pbtranscript.tasks.cluster_bins:1")]

    # run ice_partial on bins
    b4 = [("pbtranscript.tasks.create_chunks:1", "pbtranscript.tasks.ice_partial_cluster_bins:0"),
          ("pbtranscript.tasks.cluster_bins:0", "pbtranscript.tasks.ice_partial_cluster_bins:1"),
          (ccs_ds, "pbtranscript.tasks.ice_partial_cluster_bins:2")]

    # gather chunked nfl pickles in each cluster bin.
    b5 = [("pbtranscript.tasks.create_chunks:1", "pbtranscript.tasks.gather_ice_partial_cluster_bins_pickle:0"),
          ("pbtranscript.tasks.ice_partial_cluster_bins:0", "pbtranscript.tasks.gather_ice_partial_cluster_bins_pickle:1")]

    # run ice_polish (quiver|arrow) on bins
    b6 = [("pbtranscript.tasks.create_chunks:2", "pbtranscript.tasks.ice_polish_cluster_bins:0"),
          ("pbtranscript.tasks.gather_ice_partial_cluster_bins_pickle:0", "pbtranscript.tasks.ice_polish_cluster_bins:1"),
          (subreads_ds, "pbtranscript.tasks.ice_polish_cluster_bins:2")]

    # gather polished isoforms in each cluster bin
    b7 = [("pbtranscript.tasks.create_chunks:2", "pbtranscript.tasks.gather_polished_isoforms_in_each_bin:0"),
          ("pbtranscript.tasks.ice_polish_cluster_bins:0", "pbtranscript.tasks.gather_polished_isoforms_in_each_bin:1")]

    # Combine results from all cluster bins
    b8 = [("pbtranscript.tasks.create_chunks:0", "pbtranscript.tasks.combine_cluster_bins:0"),
          ("pbtranscript.tasks.gather_polished_isoforms_in_each_bin:0", "pbtranscript.tasks.combine_cluster_bins:1")]

    # pbreports isoseq_cluster
    b9 = [("pbtranscript.tasks.combine_cluster_bins:0", "pbreports.tasks.isoseq_cluster:0"), # draft consensus isoforms
          ("pbtranscript.tasks.combine_cluster_bins:1", "pbreports.tasks.isoseq_cluster:1"), # json report
          ("pbtranscript.tasks.combine_cluster_bins:4", "pbreports.tasks.isoseq_cluster:2"), # HQ isoforms fastq
          ("pbtranscript.tasks.combine_cluster_bins:6", "pbreports.tasks.isoseq_cluster:3")] # LQ isoforms fastq

    # Clean up ICE intermediate files in all cluster bins
    b10 = [("pbtranscript.tasks.create_chunks:0", "pbtranscript.tasks.ice_cleanup:0"),
           ("pbtranscript.tasks.gather_polished_isoforms_in_each_bin:0", "pbtranscript.tasks.ice_cleanup:1")]
    return b1 + b2 + b3 + b4 + b5 + b6 + b7 + b8 + b9 + b10

def _core_isoseq_collapse(hq_isoforms_fq, gmap_ref_ds, sample_prefix_pickle):
    """Core isoseq collapse mapped isoforms pipeline.
    """
    b1 = [(hq_isoforms_fq, "pbtranscript.tasks.map_isoforms_to_genome:0"),
          (gmap_ref_ds, "pbtranscript.tasks.map_isoforms_to_genome:1")]
    b2 = [(hq_isoforms_fq, "pbtranscript.tasks.post_mapping_to_genome:0"),
          ("pbtranscript.tasks.map_isoforms_to_genome:0", "pbtranscript.tasks.post_mapping_to_genome:1"),
          (sample_prefix_pickle, "pbtranscript.tasks.post_mapping_to_genome:2")]
    return b1 + b2

def _core_isoseq2_collapse(ws_json, hq_isoforms_fq, gmap_ref_ds, sample_to_uc_pickle_json):
    """Core isoseq2 collapse mapped isoforms pipeline.
    """
    b1 = [(hq_isoforms_fq, "pbtranscript.tasks.map_isoforms_to_genome:0"),
          (gmap_ref_ds, "pbtranscript.tasks.map_isoforms_to_genome:1")]
    b2 = [(ws_json, "pbtranscript2tools.tasks.post_mapping_to_genome:0"),
          (hq_isoforms_fq, "pbtranscript2tools.tasks.post_mapping_to_genome:1"),
          ("pbtranscript.tasks.map_isoforms_to_genome:0", "pbtranscript2tools.tasks.post_mapping_to_genome:2"),
          (sample_to_uc_pickle_json, "pbtranscript2tools.tasks.post_mapping_to_genome:3")]
    return b1 + b2


def _core_isoseq2_cluster(subreads_ds, ccs_ds, flnc_ds, nfl_ds):
    """Core IsoSeq2 Cluster"""
    def f(s):
        return 'pbtranscript2tools.tasks.' + s
    b0 = [(subreads_ds, f('sanity_check_params:0'))]
    b1 = [(subreads_ds, f('create_workspace:0')),
          (flnc_ds, f('create_workspace:1')),
          (nfl_ds, f('create_workspace:2')),
          (ccs_ds, f('create_workspace:3'))]
    b2 = [(f('create_workspace:0'), f('precluster:0'))] # ws.json
    b3 = [(f('create_workspace:0'), f('cluster:0')), # ws.json
          (f('precluster:0'), f('cluster:1'))] # precluster_bins.txt
    b4 = [(f('create_workspace:0'), f('collect_cluster:0')), # ws.json
          (f('cluster:0'), f('collect_cluster:1'))] # cluster out sentinel file
    b5 = [(f('create_workspace:0'), f('polish:0')), # ws.json
          (f('collect_cluster:0'), f('polish:1'))] # collect_cluster_chunk_prefixes.txt
    b6 = [(f('create_workspace:0'), f('collect_polish:0')), # ws.json
          (f('polish:0'), f('collect_polish:1'))] # polish_done.txt
    # b7: pbreports isoseq_cluster
    b7 = [(f('collect_polish:2'), "pbreports.tasks.isoseq_cluster:0"), # draft consensus isoforms fasta
          (f('collect_polish:1'), "pbreports.tasks.isoseq_cluster:1"), # json report
          (f('collect_polish:5'), "pbreports.tasks.isoseq_cluster:2"), # HQ isoforms fastq
          (f('collect_polish:8'), "pbreports.tasks.isoseq_cluster:3")] # LQ isoforms fastq
    # b8: clean up temporary files and dirs.
    b8 = [(f('create_workspace:0'), f('clean_up:0')), # ws.json
          (f('collect_polish:0'), f('clean_up:1'))] # report.csv, used to trigger clean up after collect_polish
    return b0 + b1 + b2 + b3 + b4 + b5 + b6 + b7 + b8


ISOSEQ_TASK_OPTIONS = dict(CCS_TASK_OPTIONS)
ISOSEQ_TASK_OPTIONS.update({
    "pbccs.task_options.min_passes":0,
    "pbccs.task_options.min_length":50,
    "pbccs.task_options.max_length":15000,
    "pbccs.task_options.min_zscore":-9999,
    "pbccs.task_options.max_drop_fraction":0.80,
    "pbccs.task_options.min_predicted_accuracy":0.80,
    "pbccs.task_options.polish":False
})


@sa3_register("sa3_ds_isoseq_classify", "Iso-Seq Classify Only", "0.2.0",
              tags=(Tags.MAP, Tags.CCS, Tags.ISOSEQ),
              task_options=ISOSEQ_TASK_OPTIONS)
def ds_isoseq_classify():
    """
    Partial Iso-Seq pipeline (classify step only), starting from subreads.
    """
    return _core_isoseq_classify("pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0")


@sa3_register("sa3_ds_isoseq", "Iso-Seq", "0.2.0",
              tags=(Tags.MAP, Tags.CCS, Tags.ISOSEQ),
              task_options=ISOSEQ_TASK_OPTIONS)
def ds_isoseq():
    """
    Main Iso-Seq pipeline, starting from subreads.
    """
    b1 = _core_isoseq_classify("pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0")
    b2 = _core_isoseq_cluster_chunk_by_bins(subreads_ds=Constants.ENTRY_DS_SUBREAD,
                                            ccs_ds="pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0",
                                            flnc_ds="pbtranscript.tasks.classify:1",
                                            nfl_ds="pbtranscript.tasks.classify:2")
    return b1 + b2


@sa3_register("sa3_ds_isoseq_with_genome", "Iso-Seq with Mapping", "0.2.0",
              tags=(Tags.MAP, Tags.CCS, Tags.ISOSEQ),
              task_options=ISOSEQ_TASK_OPTIONS)
def ds_isoseq_with_genome():
    """
    Main Iso-Seq pipeline, starting from subreads, requiring a reference genome GMAP dataset.
    """
    b1 = _core_isoseq_classify("pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0")
    b2 = _core_isoseq_cluster_chunk_by_bins(subreads_ds=Constants.ENTRY_DS_SUBREAD,
                                            ccs_ds="pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0",
                                            flnc_ds="pbtranscript.tasks.classify:1",
                                            nfl_ds="pbtranscript.tasks.classify:2")
    b3 = _core_isoseq_collapse(hq_isoforms_fq="pbtranscript.tasks.combine_cluster_bins:4",
                               gmap_ref_ds=Constants.ENTRY_DS_GMAPREF,
                               sample_prefix_pickle="pbtranscript.tasks.combine_cluster_bins:7")
    return b1 + b2 + b3


@sa3_register("sa3_ds_isoseq2", "Iso-Seq 2 [Beta]", "0.1.0",
              tags=(Tags.CCS, Tags.ISOSEQ, Tags.BETA),
              task_options=ISOSEQ_TASK_OPTIONS)
def ds_isoseq2():
    """
    Main Iso-Seq 2 pipeline, starting from subreads.
    """
    b1 = _core_isoseq_classify("pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0")
    b2 = _core_isoseq2_cluster(subreads_ds=Constants.ENTRY_DS_SUBREAD,
                               ccs_ds="pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0",
                               flnc_ds="pbtranscript.tasks.classify:1",
                               nfl_ds="pbtranscript.tasks.classify:2")
    return b1 + b2


@sa3_register("sa3_ds_isoseq2_with_genome", "Iso-Seq 2 with Mapping [Beta]", "0.1.0",
              tags=(Tags.MAP, Tags.CCS, Tags.ISOSEQ, Tags.BETA),
              task_options=ISOSEQ_TASK_OPTIONS)
def ds_isoseq2_with_genome():
    """
    Main Iso-Seq 2 with genome pipeline, starting from subreads, end at collapsed isoform families.
    """
    b1 = ds_isoseq2()
    b2 = _core_isoseq2_collapse(ws_json="pbtranscript2tools.tasks.create_workspace:0", # ws.json
                                hq_isoforms_fq="pbtranscript2tools.tasks.collect_polish:5", # all_arrowed_hq.fq
                                gmap_ref_ds=Constants.ENTRY_DS_GMAPREF, # gmap reference ds
                                sample_to_uc_pickle_json="pbtranscript2tools.tasks.collect_polish:10") # sample_to_uc_pickle.json
    return b1 + b2


@sa3_register("pb_isoseq_classify", "Internal Iso-Seq Classify Only for tests", "0.2.0",
              tags=(Tags.MAP, Tags.CCS, Tags.ISOSEQ))
def pb_isoseq_classify():
    """
    Partial Iso-Seq pipeline (classify step only), starting from ccs.
    This pipeline was added to test isoseq-classify with customer primers on
    the only data that we currently have (which could not ccs-ed by ccs).
    """
    return _core_isoseq_classify(ccs_ds=Constants.ENTRY_DS_CCS)


@sa3_register("pb_isoseq", "Internal Iso-Seq pipeline", "0.2.0", tags=(Tags.MAP, Tags.CCS, Tags.ISOSEQ, Tags.INTERNAL))
def pb_isoseq():
    """
    Internal Iso-Seq pipeline starting from an existing CCS dataset.
    """
    b1 = _core_isoseq_classify(Constants.ENTRY_DS_CCS)
    b2 = _core_isoseq_cluster_chunk_by_bins(subreads_ds=Constants.ENTRY_DS_SUBREAD,
                                            ccs_ds=Constants.ENTRY_DS_CCS,
                                            flnc_ds="pbtranscript.tasks.classify:1",
                                            nfl_ds="pbtranscript.tasks.classify:2")
    return b1 + b2


@sa3_register("pb_isoseq_cluster", "Internal Iso-Seq clustering pipeline", "0.2.0", tags=(Tags.ISOSEQ, Tags.INTERNAL,))
def pb_isoseq_cluster():
    return _core_isoseq_cluster_chunk_by_bins(subreads_ds=Constants.ENTRY_DS_SUBREAD,
                                              ccs_ds=Constants.ENTRY_DS_CCS,
                                              flnc_ds=to_entry("e_flnc_fa"),
                                              nfl_ds=to_entry("e_nfl_fa"))

@sa3_register("pb_isoseq_cluster_with_genome", "Internal Iso-Seq clustering with mapping", "0.2.0",
              tags=(Tags.MAP, Tags.CCS, Tags.ISOSEQ, Tags.INTERNAL),
              task_options=ISOSEQ_TASK_OPTIONS)
def pb_isoseq_cluster_with_genome():
    """
    Internal Iso-Seq pipeline, starting from existing isoseq_flnc and isoseq_nfl datasets,
    continue to collapse, count and filter isoforms, requiring a reference genome GMAP dataset.
    """
    b1 = _core_isoseq_cluster_chunk_by_bins(subreads_ds=Constants.ENTRY_DS_SUBREAD,
                                            ccs_ds=Constants.ENTRY_DS_CCS,
                                            flnc_ds=to_entry("e_flnc_fa"),
                                            nfl_ds=to_entry("e_nfl_fa"))
    b2 = _core_isoseq_collapse(hq_isoforms_fq="pbtranscript.tasks.combine_cluster_bins:4",
                               gmap_ref_ds=Constants.ENTRY_DS_GMAPREF,
                               sample_prefix_pickle="pbtranscript.tasks.combine_cluster_bins:7")
    return b1 + b2


@sa3_register("pb_isoseq_collapse", "Internal Iso-Seq Collapsing pipeline", "0.2.0", tags=(Tags.ISOSEQ, Tags.INTERNAL,))
def pb_isoseq_collapse():
    """
    Internal Iso-Seq pipeline, starting from an existing Iso-Seq job, continuing to collapse,
    continue to collapse, count and filter isoforms, requiring a reference genome GMAP dataset.
    """
    return _core_isoseq_collapse(hq_isoforms_fq=to_entry("hq_isoforms_fq"),
                                 gmap_ref_ds=Constants.ENTRY_DS_GMAPREF,
                                 sample_prefix_pickle=to_entry("sample_prefix_pickle"))


@sa3_register("pb_isoseq2_cluster", "Internal Iso-Seq2 clustering pipeline", "0.1.0", tags=(Tags.ISOSEQ, Tags.INTERNAL,))
def pb_isoseq2_cluster():
    return _core_isoseq2_cluster(subreads_ds=Constants.ENTRY_DS_SUBREAD,
                                 ccs_ds=Constants.ENTRY_DS_CCS,
                                 flnc_ds=to_entry("e_flnc_fa"),
                                 nfl_ds=to_entry("e_nfl_fa"))


@sa3_register("sa3_ds_subreads_to_fastx", "Convert BAM to FASTX", "0.1.0", tags=(Tags.CONVERTER,))
def ds_subreads_to_fastx():
    """
    Export SubreadSet to FASTA and FASTQ formats
    """
    b1 = [(Constants.ENTRY_DS_SUBREAD, "pbcoretools.tasks.filterdataset:0")]
    b2 = _core_export_fastx("pbcoretools.tasks.filterdataset:0")
    return b1 + b2


# XXX note that this pipeline is designed to be run as part of the import-fasta
# endpoint in smrtlink
@sa3_register("sa3_ds_fasta_to_reference", "Convert FASTA to ReferenceSet", "0.1.0", tags=(Tags.CONVERTER,Tags.INTERNAL))
def ds_fasta_to_reference():
    """
    Convert a FASTA file to a ReferenceSet
    """
    return [(Constants.ENTRY_REF_FASTA, "pbcoretools.tasks.fasta_to_reference:0")]


@sa3_register("sa3_fasta_to_gmap_reference", "Convert FASTA to GmapReferenceSet", "0.1.0", tags=(Tags.CONVERTER,Tags.INTERNAL))
def ds_fasta_to_reference():
    """
    Convert a FASTA file to a GmapReferenceSet
    """
    return [(Constants.ENTRY_REF_FASTA, "pbcoretools.tasks.fasta_to_gmap_reference:0")]


@sa3_register("pb_slimbam_reseq", "Resequencing starting from internal BAM", "0.1.0", tags=(Tags.CONVERTER,Tags.INTERNAL,Tags.DEV))
def pb_slimbam_reseq():
    b1 = [(Constants.ENTRY_DS_SUBREAD, "pbcoretools.tasks.slimbam:0")]
    return b1 + ds_fat_resequencing("pbcoretools.tasks.slimbam:0")


@sa3_register("pb_slimbam_barcode", "Resequencing starting from internal BAM", "0.1.0", tags=(Tags.CONVERTER,Tags.INTERNAL,Tags.DEV))
def pb_slimbam_barcode():
    b1 = [(Constants.ENTRY_DS_SUBREAD, "pbcoretools.tasks.slimbam:0")]
    return b1 + _core_barcode("pbcoretools.tasks.slimbam:0")


# XXX obsolete due to multiplexing requirement
def _core_minorseq(ds_ccs, ds_ref):
    align = [
        (ds_ccs, "pbalign.tasks.align_minorvariants:0:0"),
        (ds_ref, "pbalign.tasks.align_minorvariants:0:1")
    ]
    fuse = [
        ("pbalign.tasks.align_minorvariants:0", "minorseq.tasks.fuse:0")
    ]
    align2 = [
        (ds_ccs, "pbalign.tasks.align_minorvariants:1:0"),
        ("minorseq.tasks.fuse:0", "pbalign.tasks.align_minorvariants:1:1")
    ]
    cleric = [
        ("pbalign.tasks.align_minorvariants:1:0", "minorseq.tasks.cleric:0"),
        (ds_ref, "minorseq.tasks.cleric:1"),
        ("minorseq.tasks.fuse:0", "minorseq.tasks.cleric:2")
    ]
    juliet = [
        ("minorseq.tasks.cleric:0", "minorseq.tasks.juliet:0")
    ]
    report = [
        ("minorseq.tasks.juliet:1", "pbreports.tasks.minor_variants_report:0")
    ]
    return align + fuse + align2 + cleric + juliet + report


def _core_minorseq_multiplexed(ds_ccs, ds_ref):
    align = [
        (ds_ccs, "pbalign.tasks.align_minorvariants:0"),
        (ds_ref, "pbalign.tasks.align_minorvariants:1")
    ]
    julietflow = [
        ("pbalign.tasks.align_minorvariants:0", "pysiv2.tasks.minor_variants:0"),
        (ds_ref, "pysiv2.tasks.minor_variants:1"),
        (ds_ccs, "pysiv2.tasks.minor_variants:2")
    ]
    report = [
        ("pysiv2.tasks.minor_variants:0", "pbreports.tasks.minor_variants_report:0")
    ]
    return align + julietflow + report


@sa3_register("pb_minorseq", "Minor Variants analysis starting from CCS", "0.1.0", tags=(Tags.INTERNAL,Tags.MINORVAR))
def pb_minorseq_from_ccs():
    return _core_minorseq_multiplexed(Constants.ENTRY_DS_CCS, Constants.ENTRY_DS_REF)


MV_OPTS = {
    "pbccs.task_options.min_predicted_accuracy": 0.99,
    "pbccs.task_options.rich_qvs": True,
    "juliet.task_options.mode_phasing": True
}

@sa3_register("sa3_ds_minorseq", "Minor Variants Analysis [Beta]", "0.2.0", tags=(Tags.MINORVAR,Tags.BETA), task_options=MV_OPTS)
def ds_minorseq():
    return _core_minorseq_multiplexed("pbsmrtpipe.pipelines.sa3_ds_ccs:pbccs.tasks.ccs:0", Constants.ENTRY_DS_REF)


MV_BC_OPTS = dict(MV_OPTS)
MV_BC_OPTS.update({
    "pbcoretools.task_options.other_filters": "bq>45"
})
MV_BC_OPTS.update(BARCODING_OPTIONS)
@sa3_register("pb_barcode2_minorseq", "Minor Variants Analysis with Barcoding (Internal Testing)", "0.2.0", tags=(Tags.MINORVAR,Tags.BARCODE,Tags.INTERNAL), task_options=MV_BC_OPTS)
def pb_barcode2_minorseq():
    return _core_minorseq_multiplexed("pbsmrtpipe.pipelines.pb_barcode2_ccs:pbccs.tasks.ccs:0", Constants.ENTRY_DS_REF)


def _core_sv(ds_subread, ds_ref):
    sample = [(ds_subread, 'pbsvtools.tasks.make_samples:0')]
    prepare = [(ds_ref, 'pbsvtools.tasks.prepare_reference:0')]
    config = [
        (ds_subread, 'pbsvtools.tasks.config:0')
    ]
    align = [
        ('pbsvtools.tasks.config:0', 'pbsvtools.tasks.align:0'),
        (ds_subread, 'pbsvtools.tasks.align:1'),
        ('pbsvtools.tasks.prepare_reference:0', 'pbsvtools.tasks.align:2'),
        ('pbsvtools.tasks.make_samples:0', 'pbsvtools.tasks.align:3'),
        ('pbsvtools.tasks.align:0', 'pbsvtools.tasks.split_alignments_by_sample:0')
    ]
    call = [
        ('pbsvtools.tasks.config:0', 'pbsvtools.tasks.call:0'),
        ('pbsvtools.tasks.align:0', 'pbsvtools.tasks.call:1'),
        ('pbsvtools.tasks.prepare_reference:0', 'pbsvtools.tasks.call:2'),
        ('pbsvtools.tasks.prepare_reference:1', 'pbsvtools.tasks.call:3'),
        ('pbsvtools.tasks.align:0', 'pbsvtools.tasks.sort_sv:0'),
        ('pbsvtools.tasks.call:0', 'pbsvtools.tasks.sort_sv:1'),
        ('pbsvtools.tasks.call:1', 'pbsvtools.tasks.sort_sv:2')
    ]
    report = [
        ('pbsvtools.tasks.sort_sv:0', 'pbsvtools.tasks.make_reports:0'), # bed
        ('pbsvtools.tasks.make_reports:0', 'pbreports.tasks.structural_variants_report:0'),
        ('pbsvtools.tasks.make_reports:1', 'pbreports.tasks.structural_variants_report:1')
    ]
    return sample + prepare + config + align + call + report


@sa3_register("sa3_ds_sv", "Structural Variant Calling", "0.1.0", tags=(Tags.SV,))
def ds_sv():
    return _core_sv(Constants.ENTRY_DS_SUBREAD, Constants.ENTRY_DS_REF)


@sa3_register("pb_mapping_stats", "Generate Mapping Stat Report", "0.1.0", tags=(Tags.MAP, Tags.RPT, Tags.INTERNAL))
def mapping_stats():
    return [(Constants.ENTRY_DS_ALIGN, "pbreports.tasks.mapping_stats:0")]


@sa3_register("pb_mapping_reports", "Generate All Mapping Reports", "0.1.0", tags=(Tags.MAP, Tags.RPT, Tags.INTERNAL))
def mapping_reports():
    return mapping_stats() + [
        (Constants.ENTRY_DS_ALIGN, "pbreports.tasks.summarize_coverage:0"),
        (Constants.ENTRY_DS_REF, "pbreports.tasks.summarize_coverage:1"),
        (Constants.ENTRY_DS_REF, "pbreports.tasks.coverage_report:0"),
        ("pbreports.tasks.summarize_coverage:0", "pbreports.tasks.coverage_report:1")
    ]


# XXX the next two pipelines are officially obsolete, but we keep them around
# (in reduced form) to preserve labeling
@sa3_register("sa3_ds_barcode_laa", "LAA with Barcoding", "0.3.0",
              tags=(Tags.BARCODE,Tags.LAA,Tags.INTERNAL))
def ds_barcode_laa_old():
    """
    SubreadSet barcoding pipeline
    """
    return _core_barcode_old() + _core_laa("pbcoretools.tasks.bam2bam_barcode:0")


@sa3_register("sa3_ds_barcode_ccs", "CCS with Barcoding", "0.3.0",
              tags=(Tags.BARCODE,Tags.CCS,Tags.INTERNAL))
def ds_barcode_ccs_old():
    """
    SubreadSet barcoding pipeline
    """
    return _core_barcode_old() + _core_ccs("pbcoretools.tasks.bam2bam_barcode:0")
