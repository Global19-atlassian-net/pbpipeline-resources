README for pbpipeline-resources
===============================

This repository contains all pipeline definitions and associated view rules
required by SMRT Link and pbsmrtpipe (with the exception of report view rules,
see below).  To work with these resources you will need a Python interpreter
that has pbsmrtpipe and pbreports installed.  To make the resources available
to pbsmrtpipe or the services runner, simply run "make" and then set the
environment variable ``SMRT_PIPELINE_BUNDLE_DIR`` to point to this directory.

The resources actually used by downstream programs live in the following
directories (described in detail below):

  1. ``chunk_operators``: pbsmrtpipe chunk operators, XML format
  2. ``pipeline-datastore-view-rules``: SMRT Link download page view rules, JSON
  3. ``pipeline-template-view-rules``: SMRT Link pipeline configuration view rules, JSON
  4. ``registered-tool-contracts``: pbsmrtpipe tool contracts, JSON
  5. ``report-view-rules``: SMRT Link report view rules, JSON
  6. ``resolved-pipeline-templates``: pbsmrtpipe pipelines, JSON

Of these, only (1) and (3) should be edited in-place in this repository.  (2)
and (6) are generated automatically from Python code included in the repo, (4)
contains cached versions of automatically generated files (from Python/C++
programs), and (5) is files copied from pbreports.

Please run ``make test`` whenever you make changes to the source files
in this repository; this is required for a successful build (and pull request).


Tool Contracts
--------------

To add or replace a tool contract, simply run the appropriate tool command:

```
  $ mytool --emit-tool-contract > registered-tool-contracts/mymodule.tasks.mytool_tool_contract.json
```

This still needs to be done manually (otherwise it is impossible to validate
pipeline changes).  However existing tool contracts can now be updated in bulk
by running the following:

```
  $ module load smrttools
  $ make tool-contracts
```

Please note that this means that any tool contract may be re-generated at
any time without notice, and manual edits are discouraged and liable to be
overwritten later.


Pipelines
---------

pbsmrtpipe pipelines are defined programatically in several Python files
(currently ``pb_pipelines_falcon.py`` and ``pb_pipelines_sa3.py``), and are
dynamically converted to JSON for consumption by the tests and smrttools build.
Please consult the [pbsmrtpipe documentation] [1] for a detailed explanation 
of how the pipelines are written.

[1]: http://pbsmrtpipe.readthedocs.io/en/master/pipeline_design.html

Note that if these are out of sync with the tool contracts, or the correct
environment variable has not been set, the sanity test may fail.  The most
common reasons for this are more or fewer input files for a task than declared
in the tool contract, or a file binding changing type (i.e. passing a CSV
output from one task as the JSON input of a subsequent task).


Chunk Operators
---------------

These are defined by static XML instead of JSON, but are also relatively simple
data structures, also documented as part of pbsmrtpipe.  Since they refer to
specific tasks, as is the case for pipelines the chunk operators may fail
sanity testing if the registered tool contracts are not in sync.  They may
also fail if they refer to a scatter or gather task without a registered tool
contract, or if the wrong file type is passed.


Pipeline Template View Rules
----------------------------

These JSON files control the visibility of pipeline options in the SMRT LINK
UI.  The structure is very simple:

```
  {
    "id": "pbsmrtpipe.pipelines.sa3_ds_laa",
    "name": "Override Pipeline Display Name",
    "description": "Override Description",
    "taskOptions": [
      {"id": "pblaa.task_options.result_file",              "hidden": true,  "advanced": true},
      {"id": "pblaa.task_options.min_length",               "hidden": false, "advanced": false}
    ]
  }
```

The default visibility is ``hidden=false advanced=true``, which means an
option appears in the advanced settings window.  Set ``hidden=true`` to remove
it from the UI entirely, or set ``advanced=false`` to make it appear in the
main window.

Note that the name and description fields are currently ignored, although they
are still required.


Pipeline Datastore View Rules
-----------------------------

These rules are also defined programmatically in ``pb_pipeline_view_rules.py``,
which is later used to generate JSON files for consumption by SMRT Link.
They control the visibility of pipeline outputs in the downloads section of
the analysis results, and are now explicitly required for any file that should
be visible to users.  By default, all outputs (except pbsmrtpipe log files) are
invisible if not otherwise specified.  An example of how visibility is control
looks like:

```
  @register_pipeline_rules("sa3_ds_ccs")
  def ccs_view_rules():
      whitelist = _to_whitelist([
          ("pbcoretools.tasks.bam2fastq_ccs-out-0", FileTypes.TGZ),
          ("pbcoretools.tasks.bam2fasta_ccs-out-0", FileTypes.TGZ),
          ("pbccs.tasks.ccs-out-0", FileTypes.DS_CCS)
      ])
      blacklist = _to_blacklist([
          ("pbreports.tasks.ccs_report-out-0", FileTypes.REPORT)
      ])
      return whitelist + blacklist + _log_view_rules()
```

The rules are keyed by output file ``sourceId``, which for any pbsmrtpipe task
output takes the form ``$taskId-out-$idx``, and the file type.  In this
example we want to display tar-gzipped FASTA and FASTQ files and the CCS
DataSet XML on the downloads page, but not the CCS report JSON (which is
already consumed and displayed by the results page, unaffected by these
view rules).  (We do not actually need to define a blacklist any more - this is
mostly a holdover from previous behavior.)

It is also possible to override the file label, for example when the same task
is used in different pipelines:

```
  hgap_overrides = [
        ("pbcoretools.tasks.contigset2fasta-out-0", FileTypes.FASTA, False, "Polished Assembly"),
        ("genomic_consensus.tasks.variantcaller-out-2", FileTypes.DS_CONTIG, False, "Polished Assembly"),
        ("genomic_consensus.tasks.variantcaller-out-3", FileTypes.FASTQ, False, "Polished Assembly"),
        ("pbcoretools.tasks.fasta2referenceset-out-0", FileTypes.DS_REF, False, "Draft Assembly")
  ]
```


Report View Rules
-----------------

These continue to live under pbreports (in `pbreports/report/specs`) for now;
as part of the smrttools build they are copied over to the pbpipeline-resources
bundle, so the two locations are guaranteed to be in sync.
