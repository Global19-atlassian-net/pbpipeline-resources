import logging

from pbcommand.models.common import to_pipeline_ns

from pbsmrtpipe.core import register_pipeline

from pb_pipelines_sa3 import Constants, Tags, _core_align, _core_gc

log = logging.getLogger(__name__)


def dev_register(relative_id, display_name, tags=(), task_options=None, version="0.1.0"):
    pipeline_id = to_pipeline_ns(relative_id)
    ptags = list(set(tags + (Tags.DENOVO, )))
    return register_pipeline(pipeline_id, display_name, version, tags=ptags, task_options=task_options)

def _get_falcon_pipeline(i_cfg, i_fasta_fofn):
    """Basic falcon pipeline components.
    """
    b0 = [
          (i_cfg,
                        'falcon_ns2.tasks.task_falcon_config:0'),
          (i_fasta_fofn,
                        'falcon_ns2.tasks.task_falcon_config:1'),
          ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon_make_fofn_abs:0'),
    ]
    # dazzler build raw_reads.db
    dzbr = [
            ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_build_raw:0'),
            ('falcon_ns2.tasks.task_falcon_make_fofn_abs:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_build_raw:1'),
    ]
    # dazzler TANmask split/run/combine
    dzts = [
            ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_tan_split:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_build_raw:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_tan_split:1'),
    ]
    dztr = [
            ('falcon_ns2.tasks.task_falcon0_dazzler_tan_split:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_tan_apply_jobs:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_tan_split:1',
                        'falcon_ns2.tasks.task_falcon0_dazzler_tan_apply_jobs:1'),
    ]
    dztc = [
            ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_tan_combine:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_build_raw:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_tan_combine:1'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_tan_apply_jobs:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_tan_combine:2'),
    ]
    # dazzler daligner split/run/combine
    dzds = [
            ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_daligner_split:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_tan_combine:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_daligner_split:1'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_build_raw:1',
                        'falcon_ns2.tasks.task_falcon0_dazzler_daligner_split:2'), # length_cutoff_fn
    ]
    dzdr = [
            ('falcon_ns2.tasks.task_falcon0_dazzler_daligner_split:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_daligner_apply_jobs:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_daligner_split:1',
                        'falcon_ns2.tasks.task_falcon0_dazzler_daligner_apply_jobs:1'),
    ]
    dzdc = [
            ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_daligner_combine:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_build_raw:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_daligner_combine:1'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_daligner_apply_jobs:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_daligner_combine:2'),
    ]
    # dazzler LAmerge split/run/combine
    dzls = [
            ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_lamerge_split:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_daligner_combine:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_lamerge_split:1'),
    ]
    dzlr = [
            ('falcon_ns2.tasks.task_falcon0_dazzler_lamerge_split:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_lamerge_apply_jobs:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_lamerge_split:1',
                        'falcon_ns2.tasks.task_falcon0_dazzler_lamerge_apply_jobs:1'),
    ]
    dzlc = [
            ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_lamerge_combine:0'),
            ('falcon_ns2.tasks.task_falcon0_dazzler_lamerge_apply_jobs:0',
                        'falcon_ns2.tasks.task_falcon0_dazzler_lamerge_combine:1'),
    ]
    """
def run_dazzler_build(input_files, output_files, actual_db_fn):
    i_general_config_fn, i_fofn_fn = input_files
    db_fn, length_cutoff_fn = output_files
def run_dazzler_tan_split(input_files, output_files):
    i_general_config_fn, db_fn, = input_files
    o_split_fn, o_bash_fn, = output_files
def run_dazzler_tan_combine(input_files, output_files, actual_db_fn):
    i_general_config_fn, i_db_fn, i_gathered_fn, = input_files
    o_db_fn, = output_files
def run_dazzler_daligner_split(input_files, output_files):
    i_general_config_fn, i_db_fn, i_length_cutoff_fn, = input_files
    o_split_fn, o_bash_fn, = output_files
def run_dazzler_daligner_combine(input_files, output_files, actual_db_fn):
    i_general_config_fn, i_db_fn, i_gathered_fn, = input_files
    o_las_paths_fn, = output_files
def run_dazzler_lamerge_split(input_files, output_files, db_prefix):
    i_general_config_fn, i_las_paths_fn, = input_files
    o_split_fn, o_bash_fn, = output_files
def run_dazzler_lamerge_combine(input_files, output_files):
    i_general_config_fn, i_gathered_fn, = input_files
    o_las_paths_fn, o_block2las_fn, = output_files
def run_cns_split(input_files, output_files):
    p_id2las_fn, raw_reads_db_fn, general_config_fn, length_cutoff_fn, = input_files
    all_units_of_work_fn, bash_template_fn, = output_files
def run_report_preassembly_yield(input_files, output_files):
    i_general_config_fn, i_preads_fofn_fn, i_raw_reads_db_fn, i_length_cutoff_fn = input_files
    """
    #br0 = [
    #      ('falcon_ns2.tasks.task_falcon_config:0',
    #                    'falcon_ns2.tasks.task_falcon0_build_rdb:0'),
    #      ('falcon_ns2.tasks.task_falcon_make_fofn_abs:0',
    #                    'falcon_ns2.tasks.task_falcon0_build_rdb:1'),
    #     ]
    #brs = [
    #        ('falcon_ns2.tasks.task_falcon0_build_rdb:0',
    #                    'falcon_ns2.tasks.task_falcon0_run_daligner_split:0'),
    #        ('falcon_ns2.tasks.task_falcon0_build_rdb:1',
    #                    'falcon_ns2.tasks.task_falcon0_run_daligner_split:1'),
    #]
    #br1 = [
    #        ('falcon_ns2.tasks.task_falcon0_run_daligner_split:0',
    #                    'falcon_ns2.tasks.task_falcon0_run_daligner_jobs:0'),
    #        ('falcon_ns2.tasks.task_falcon0_run_daligner_split:1',
    #                    'falcon_ns2.tasks.task_falcon0_run_daligner_jobs:1'),
    #]
    #br2 = [
    #        ('falcon_ns2.tasks.task_falcon0_run_daligner_jobs:0',
    #                    'falcon_ns2.tasks.task_falcon0_run_daligner_find_las:0'),
    #]
    #br3 = [
    #        ('falcon_ns2.tasks.task_falcon0_build_rdb:0',
    #                    'falcon_ns2.tasks.task_falcon0_run_las_merge_split:0'),
    #        ('falcon_ns2.tasks.task_falcon0_run_daligner_find_las:0',
    #                    'falcon_ns2.tasks.task_falcon0_run_las_merge_split:1'),
    #]
    ## execute LAmerge scripts (e.g., m_00001/merge_00001.sh) to create raw_reads.*.las
    #br4 = [
    #        ('falcon_ns2.tasks.task_falcon0_run_las_merge_split:0',
    #                    'falcon_ns2.tasks.task_falcon0_run_las_merge_jobs:0'),
    #        ('falcon_ns2.tasks.task_falcon0_run_las_merge_split:1',
    #                    'falcon_ns2.tasks.task_falcon0_run_las_merge_jobs:1'),
    #]
    #br5 = [
    #        ('falcon_ns2.tasks.task_falcon0_run_las_merge_jobs:0',
    #                    'falcon_ns2.tasks.task_falcon0_run_las_merge_post_gather:0'),
    #]
    br6 = [
            ('falcon_ns2.tasks.task_falcon0_dazzler_lamerge_combine:1',
                        'falcon_ns2.tasks.task_falcon0_run_cns_split:0'), #block2las
            ('falcon_ns2.tasks.task_falcon0_dazzler_build_raw:0',
                        'falcon_ns2.tasks.task_falcon0_run_cns_split:1'), #db
            ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_falcon0_run_cns_split:2'), #config
            ('falcon_ns2.tasks.task_falcon0_dazzler_build_raw:1',
                        'falcon_ns2.tasks.task_falcon0_run_cns_split:3'), #length_cutoff
    ]
    # execute LA4Falcon scripts (e.g., preads/c_00001.sh) to create out.0000*.fasta
    br7 = [
            ('falcon_ns2.tasks.task_falcon0_run_cns_split:0',
                        'falcon_ns2.tasks.task_falcon0_run_cns_jobs:0'),
            ('falcon_ns2.tasks.task_falcon0_run_cns_split:1',
                        'falcon_ns2.tasks.task_falcon0_run_cns_jobs:1'),
    ]
    br8 = [
            ('falcon_ns2.tasks.task_falcon0_run_cns_jobs:0',
                        'falcon_ns2.tasks.task_falcon0_run_cns_post_gather:0'),
    ]
    report_pay = [
          ('falcon_ns2.tasks.task_falcon_config:0',
                        'falcon_ns2.tasks.task_report_preassembly_yield:0'), # config
          ('falcon_ns2.tasks.task_falcon0_run_cns_post_gather:0',
                        'falcon_ns2.tasks.task_report_preassembly_yield:1'), # preads.fofn
          ('falcon_ns2.tasks.task_falcon0_dazzler_tan_combine:0',
                        'falcon_ns2.tasks.task_report_preassembly_yield:2'), # db (tan, for now)
          ('falcon_ns2.tasks.task_falcon0_dazzler_build_raw:1',
                        'falcon_ns2.tasks.task_report_preassembly_yield:3')  # length_cutoff_fn
    ]
    bp0 = [
          ('falcon_ns2.tasks.task_falcon_config:0',
                    'falcon_ns2.tasks.task_falcon1_build_pdb:0'),
          ('falcon_ns2.tasks.task_falcon0_run_cns_post_gather:0',
                    'falcon_ns2.tasks.task_falcon1_build_pdb:1'),
         ]
    bps = [
            ('falcon_ns2.tasks.task_falcon1_build_pdb:0',
                    'falcon_ns2.tasks.task_falcon1_run_daligner_split:0'),
            ('falcon_ns2.tasks.task_falcon1_build_pdb:1',
                    'falcon_ns2.tasks.task_falcon1_run_daligner_split:1'),
    ]
    bp1 = [
            ('falcon_ns2.tasks.task_falcon1_run_daligner_split:0',
                    'falcon_ns2.tasks.task_falcon1_run_daligner_jobs:0'),
            ('falcon_ns2.tasks.task_falcon1_run_daligner_split:1',
                    'falcon_ns2.tasks.task_falcon1_run_daligner_jobs:1'),
    ]
    bp2 = [
            ('falcon_ns2.tasks.task_falcon1_run_daligner_jobs:0',
                    'falcon_ns2.tasks.task_falcon1_run_daligner_find_las:0'),
    ]
    bp3 = [
            ('falcon_ns2.tasks.task_falcon1_build_pdb:0',
                    'falcon_ns2.tasks.task_falcon1_run_las_merge_split:0'),
            ('falcon_ns2.tasks.task_falcon1_run_daligner_find_las:0',
                    'falcon_ns2.tasks.task_falcon1_run_las_merge_split:1'),
    ]
    # execute LAmerge scripts (e.g., m_00001/merge_00001.sh) to create preads.*.las
    bp4 = [
            ('falcon_ns2.tasks.task_falcon1_run_las_merge_split:0',
                    'falcon_ns2.tasks.task_falcon1_run_las_merge_jobs:0'),
            ('falcon_ns2.tasks.task_falcon1_run_las_merge_split:1',
                    'falcon_ns2.tasks.task_falcon1_run_las_merge_jobs:1'),
    ]
    bp5 = [
            ('falcon_ns2.tasks.task_falcon1_run_las_merge_jobs:0',
                    'falcon_ns2.tasks.task_falcon1_run_las_merge_post_gather:0'),
    ]
    # bp4: execute db2falcon scripts (e.g., run_db2falcon.sh) to create falcon db.
    bpf = [('falcon_ns2.tasks.task_falcon1_run_las_merge_post_gather:1',
                    'falcon_ns2.tasks.task_falcon1_run_db2falcon:0'), # p_id2las
           ('falcon_ns2.tasks.task_falcon1_build_pdb:1',
                    'falcon_ns2.tasks.task_falcon1_run_db2falcon:1'), # preads.db
    ]
    basm = [
            ('falcon_ns2.tasks.task_falcon1_run_db2falcon:0',
                    'falcon_ns2.tasks.task_falcon2_run_falcon_asm:0'),  # preads4falcon.fasta
            ('falcon_ns2.tasks.task_falcon1_build_pdb:1',
                    'falcon_ns2.tasks.task_falcon2_run_falcon_asm:1'),  # preads.db
            ('falcon_ns2.tasks.task_falcon1_run_las_merge_post_gather:0',
                    'falcon_ns2.tasks.task_falcon2_run_falcon_asm:2'),  # las_fofn.json (preads.*.las)
            ('falcon_ns2.tasks.task_falcon_config:0',
                    'falcon_ns2.tasks.task_falcon2_run_falcon_asm:3'),  # config.json
            ('falcon_ns2.tasks.task_falcon1_run_db2falcon:1',
                    'falcon_ns2.tasks.task_falcon2_run_falcon_asm:4'),  # db2falcon sentinel (truly needed?)
    ]
    #### rm L*.*.raw_reads.las
    ###rm0 = [('falcon_ns2.tasks.task_falcon0_dazzler_daligner_apply_jobs:0',
    ###                'falcon_ns2.tasks.task_falcon0_rm_las:0'), # sentinels from daligner jobs
    ###]
    rm0 = []
    #### rm raw_reads.*.raw_reads.las
    ###rm1 = [('falcon_ns2.tasks.task_falcon0_run_cns_jobs:0',
    ###                'falcon_ns2.tasks.task_falcon1_rm_las:0'),
    ###       ('falcon_ns2.tasks.task_falcon0_rm_las:0',
    ###                'falcon_ns2.tasks.task_falcon1_rm_las:1'),
    ###]
    rm1 = []
    # clean up all *.las regardless
    # Note: We use the old falcon_ns namespace for this task
    # so we do not need to change option names in views and existing preset files.
    ###rm2 = [('falcon_ns2.tasks.task_falcon2_run_falcon_asm:0',
    ###                'falcon_ns.tasks.task_falcon2_rm_las:0'), # not ns2
    ###       ('falcon_ns2.tasks.task_falcon1_rm_las:0',
    ###                'falcon_ns.tasks.task_falcon2_rm_las:1'), # not ns2
    ###]
    rm2 = []
    #falcon = (b0 + br0 + brs + br1 + br2 + br3 + br4 + br5 + br6 + br7 + br8 + report_pay
    falcon = (b0 + dzbr + dzts + dztr + dztc + dzds + dzdr + dzdc + dzls + dzlr + dzlc + br6 + br7 + br8 + report_pay
            + bp0 + bps + bp1 + bp2 + bp3 + bp4 + bp5 + bpf + basm + rm0 + rm1 + rm2)
    falcon_results = dict()
    falcon_results['asm'] = 'falcon_ns2.tasks.task_falcon2_run_falcon_asm:0'
    return falcon, falcon_results

def _get_polished_falcon_pipeline():
    subreadset = Constants.ENTRY_DS_SUBREAD

    filt = [(subreadset, 'pbcoretools.tasks.filterdataset:0')]
    btf = [('pbcoretools.tasks.filterdataset:0', 'pbcoretools.tasks.bam2fasta:0')]
    ftfofn = [('pbcoretools.tasks.bam2fasta:0', 'pbcoretools.tasks.fasta2fofn:0')]

    i_fasta_fofn = 'pbcoretools.tasks.fasta2fofn:0'

    gen_cfg = [(i_fasta_fofn, 'falcon_ns.tasks.task_falcon_gen_config:0')]

    i_cfg = 'falcon_ns.tasks.task_falcon_gen_config:0'

    falcon, falcon_results = _get_falcon_pipeline(i_cfg, i_fasta_fofn)

    ref = falcon_results['asm']

    faidx = [(ref, 'pbcoretools.tasks.fasta2referenceset:0')]

    aln = 'pbalign.tasks.pbalign:0'
    ref = 'pbcoretools.tasks.fasta2referenceset:0'

    polish = _core_align("pbcoretools.tasks.filterdataset:0", ref) + _core_gc(aln, ref)
    results = dict()
    results['aln'] = aln
    results['ref'] = ref

    return ((filt + btf + ftfofn + gen_cfg + falcon + faidx + polish), results)

@dev_register("pipe_falcon_with_fofn", "Falcon FOFN Pipeline",
              tags=("local", "chunking", "internal"))
def get_task_falcon_local_pipeline2():
    """Simple falcon local pipeline.
    Use an entry-point for FASTA input.
    """
    return _get_falcon_pipeline('$entry:e_01', '$entry:e_02')[0]

@dev_register("pipe_falcon", "Falcon Pipeline",
              tags=("local", "chunking", "internal"))
def get_task_falcon_local_pipeline1():
    """Simple falcon local pipeline.
    FASTA input comes from config file.
    """
    i_cfg = '$entry:e_01'
    init = [
          (i_cfg, 'falcon_ns.tasks.task_falcon_config_get_fasta:0'),
           ]
    i_fasta_fofn = 'falcon_ns.tasks.task_falcon_config_get_fasta:0' # output from init
    return init + _get_falcon_pipeline(i_cfg, i_fasta_fofn)[0]

@dev_register("polished_falcon", "Polished Falcon Pipeline",
              tags=("chunking", "internal"))
def get_task_polished_falcon_pipeline():
    """Simple polished falcon local pipeline.
    FASTA input comes from the SubreadSet.
    """
    i_cfg = '$entry:e_01'
    subreadset = Constants.ENTRY_DS_SUBREAD

    btf = [(subreadset, 'pbcoretools.tasks.bam2fasta:0')]
    ftfofn = [('pbcoretools.tasks.bam2fasta:0', 'pbcoretools.tasks.fasta2fofn:0')]

    i_fasta_fofn = 'pbcoretools.tasks.fasta2fofn:0'

    falcon, falcon_results = _get_falcon_pipeline(i_cfg, i_fasta_fofn)

    ref = falcon_results['asm']

    faidx = [(ref, 'pbcoretools.tasks.fasta2referenceset:0')]

    ref = 'pbcoretools.tasks.fasta2referenceset:0'

    polish = _core_align(subreadset, ref) + _core_gc('pbalign.tasks.pbalign:0',
                                                     ref)

    return btf + ftfofn + falcon + faidx + polish

# Copied from pb_pipelines_sa3.py
RESEQUENCING_TASK_OPTIONS = {
    "genomic_consensus.task_options.algorithm": "best",
    "pbcoretools.task_options.other_filters": "rq >= 0.7",
    #"pbalign.task_options.algorithm_options": "-minMatch 12 -bestn 10 -minPctSimilarity 70.0 -refineConcordantAlignments",
    #"pbalign.task_options.concordant": True,
}

'''
@dev_register("polished_falcon_lean2", "Assembly (HGAP 4) without reports, v.2", tags=("internal",),
        task_options=RESEQUENCING_TASK_OPTIONS)
def get_falcon_pipeline_lean2():
    """Simple polished falcon local pipeline (sans reports).
    FASTA input comes from the SubreadSet.
    Cfg input is built from preset.xml
    """
    #falcon, _ = _get_polished_falcon_pipeline()
    subreadset = Constants.ENTRY_DS_SUBREAD

    filt = [(subreadset, 'pbcoretools.tasks.filterdataset:0')]
    btf = [('pbcoretools.tasks.filterdataset:0', 'pbcoretools.tasks.bam2fasta:0')]
    ftfofn = [('pbcoretools.tasks.bam2fasta:0', 'pbcoretools.tasks.fasta2fofn:0')]

    i_fasta_fofn = 'pbcoretools.tasks.fasta2fofn:0'

    gen_cfg = [(i_fasta_fofn, 'falcon_ns.tasks.task_falcon_gen_config:0')]

    i_cfg = 'falcon_ns.tasks.task_falcon_gen_config:0'

    falcon, falcon_results = _get_falcon_pipeline(i_cfg, i_fasta_fofn)
    asm = falcon_results['asm']
    faidx = [(asm, 'pbcoretools.tasks.fasta2referenceset:0')]

    aln = 'pbalign.tasks.pbalign:0'
    ref = 'pbcoretools.tasks.fasta2referenceset:0'
    polish = _core_align("pbcoretools.tasks.filterdataset:0", ref) + _core_gc(aln, ref)

    results = dict()
    results['aln'] = aln
    results['ref'] = ref

    pipe = (filt + btf + ftfofn + gen_cfg + falcon + faidx + polish)
    #return (pipe, results)
    return pipe
'''

@dev_register("polished_falcon_lean", "Assembly (HGAP 4) without reports", tags=("internal",),
        task_options=RESEQUENCING_TASK_OPTIONS)
def get_falcon_pipeline_lean():
    """Simple polished falcon local pipeline (sans reports).
    FASTA input comes from the SubreadSet.
    Cfg input is built from preset.xml
    """
    falcon, _ = _get_polished_falcon_pipeline()
    return falcon

@dev_register("polished_falcon_fat", "Assembly (HGAP 4)",
        task_options=RESEQUENCING_TASK_OPTIONS, version="0.2.1")
def get_falcon_pipeline_fat():
    """Same as polished_falcon_lean, but with reports.
    """
    falcon, results = _get_polished_falcon_pipeline()

    # id's of results from falcon:
    aln = 'pbalign.tasks.pbalign:0'
    ref = 'pbcoretools.tasks.fasta2referenceset:0'

    # summarize the coverage:
    sum_cov = [(aln, "pbreports.tasks.summarize_coverage:0"),
               (ref, "pbreports.tasks.summarize_coverage:1")]

    # gen polished_assembly report:
    # takes alignment summary GFF, polished assembly fastQ
    polished_report = [('pbreports.tasks.summarize_coverage:0', 'pbreports.tasks.polished_assembly:0'),
                       ('genomic_consensus.tasks.variantcaller:3', 'pbreports.tasks.polished_assembly:1')]
    mapping_report = [
        (aln, "pbreports.tasks.mapping_stats_hgap:0"),
        ("pbcoretools.tasks.filterdataset:0", "pbreports.tasks.mapping_stats_hgap:1")
    ]
    coverage_report = [
        (ref, "pbreports.tasks.coverage_report_hgap:0"),
        ("pbreports.tasks.summarize_coverage:0", "pbreports.tasks.coverage_report_hgap:1")
    ]
    fasta_out = [
        ("genomic_consensus.tasks.variantcaller:2", "pbcoretools.tasks.contigset2fasta:0")
    ]

    return falcon + sum_cov + polished_report + mapping_report + coverage_report + fasta_out

def _get_hgap_pypeflow(i_cfg, i_logging_cfg, i_subreadset):
    return [
            (i_cfg,         'falcon_ns.tasks.task_hgap_run:0'),
            (i_logging_cfg, 'falcon_ns.tasks.task_hgap_run:1'),
            (i_subreadset,  'falcon_ns.tasks.task_hgap_run:2'),
           ]

#@dev_register("hgap_cmd", "XI- Experimental Assembly (HGAP 5) without reports", tags=("internal",))
def hgap_cmd():
    # from hgap-cfg.json, logging-cfg.json, and subreads-dataset
    """Simple polished HGAP pipeline (sans reports).
    BAM input comes from the SubreadSet.
    hgap-cfg.json comes from $entry:e_01
    logging-cfg.json comes from $entry:e_02
    """
    subreadset = Constants.ENTRY_DS_SUBREAD
    hgap_cfg = '$entry:e_01'
    logging_cfg = '$entry:e_02'
    return _get_hgap_pypeflow(hgap_cfg, logging_cfg, subreadset)

@dev_register("hgap_lean", "X - Experimental Assembly (HGAP 5) without reports", tags=("internal",))
def hgap_lean():
    """GUI polished HGAP pipeline (sans reports).
    BAM input comes from the SubreadSet.
    .cfg inputs are based on pbsmrtpipe options, via task_hgap_prepare
    """
    subreadset = Constants.ENTRY_DS_SUBREAD
    hgap_prepare = [(subreadset,
                   'falcon_ns.tasks.task_hgap_prepare:0')]
    hgap_cfg =     'falcon_ns.tasks.task_hgap_prepare:0'
    logging_cfg =  'falcon_ns.tasks.task_hgap_prepare:1'
    hgap_run = _get_hgap_pypeflow(hgap_cfg, logging_cfg, subreadset)
    return hgap_prepare + hgap_run

@dev_register("hgap_fat", "Assembly (HGAP 5 beta)", tags=("internal",))
def hgap_fat():
    """GUI polished HGAP pipeline.
    BAM input comes from the SubreadSet.
    .cfg inputs are based on pbsmrtpipe options, via task_hgap_prepare
    """
    subreadset = Constants.ENTRY_DS_SUBREAD
    hgap_prepare = [(subreadset,
                   'falcon_ns.tasks.task_hgap_prepare:0')]
    hgap_cfg =     'falcon_ns.tasks.task_hgap_prepare:0'
    logging_cfg =  'falcon_ns.tasks.task_hgap_prepare:1'
    hgap_run = _get_hgap_pypeflow(hgap_cfg, logging_cfg, subreadset)
    return hgap_prepare + hgap_run
