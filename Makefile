.PHONY: clean report-view-rules pipeline-datastore-view-rules

all: bundle

test: pipeline-template-json pipeline-datastore-view-rules jsontest test-sanity

clean:
	rm -f *.pyc
	find resolved-pipeline-templates -name "*.json" | grep -v "dev_diagnostic" | xargs rm -f
	git checkout resolved-pipeline-templates/pbsmrtpipe.pipelines.dev_diagnostic*
	find pipeline-datastore-view-rules -name "*.json" | grep -v "dev_01" | grep -v "\-4.0.json" | grep -v "\-5.0.json" | xargs rm -f
	find report-view-rules -name "*.json" | grep -v "ccs_processing" | grep -v "simple_dataset" | grep -v "pbsmrtpipe" | xargs rm -f
	rm -rf pbpipeline-resources-*

test-sanity:
	$(eval PB_TOOL_CONTRACT_DIR := `readlink -f registered-tool-contracts`)
	$(eval PB_PIPELINE_TEMPLATE_DIR := `readlink -f resolved-pipeline-templates`)
	$(eval PB_CHUNK_OPERATOR_DIR := `readlink -f chunk_operators`)
	PB_TOOL_CONTRACT_DIR=$(PB_TOOL_CONTRACT_DIR) \
		PB_PIPELINE_TEMPLATE_DIR=$(PB_PIPELINE_TEMPLATE_DIR) \
		PB_CHUNK_OPERATOR_DIR=$(PB_CHUNK_OPERATOR_DIR) \
		SMRT_IGNORE_PIPELINE_BUNDLE=true \
		python -c "import os ; os.environ.pop('SMRT_PIPELINE_BUNDLE_DIR', None); import pbsmrtpipe.loader as L; L.load_all()"
	PB_TOOL_CONTRACT_DIR=$(PB_TOOL_CONTRACT_DIR) \
    PB_PIPELINE_TEMPLATE_DIR=$(PB_PIPELINE_TEMPLATE_DIR) \
		PB_CHUNK_OPERATOR_DIR=$(PB_CHUNK_OPERATOR_DIR) \
		SMRT_IGNORE_PIPELINE_BUNDLE=true \
		python -c "import os ; os.environ.pop('SMRT_PIPELINE_BUNDLE_DIR', None); import pbsmrtpipe.loader as L; L.load_and_validate_chunk_operators()"
	PB_TOOL_CONTRACT_DIR=$(PB_TOOL_CONTRACT_DIR) \
    PB_PIPELINE_TEMPLATE_DIR=$(PB_PIPELINE_TEMPLATE_DIR) \
    PB_CHUNK_OPERATOR_DIR=$(PB_CHUNK_OPERATOR_DIR) \
		SMRT_IGNORE_PIPELINE_BUNDLE=true \
		python -c "import os ; import sys; reload(sys) ; sys.setdefaultencoding('utf-8') ; os.environ.pop('SMRT_PIPELINE_BUNDLE_DIR', None); import nose.core ; nose.core.main(argv=['nosetests', '--verbose', 'pbsmrtpipe.tests.test_pb_pipelines_sanity'])"

jsontest:
	$(eval JSON := `find . -type f -name '*.json' -not -path '*/\.*' | grep -v './repos/' | grep -v './jobs-root/' | grep -v './tmp/' | grep -v 'target/scala'`)
	@for j in $(JSON); do \
		echo $$j ;\
		python -m json.tool $$j >/dev/null || exit 1 ;\
	done

show-workflow-options:
	python -c 'import pbsmrtpipe.cli; pbsmrtpipe.cli.main(["pbsmrtpipe", "show-workflow-options"])' | grep "^Option" | sed 's/.*:\ *//; s/.*\.//;' > workflow_options.txt

pipeline-template-json:
	PB_TOOL_CONTRACT_DIR=$(PB_TOOL_CONTRACT_DIR) \
		SMRT_IGNORE_PIPELINE_BUNDLE=true \
		python make_pipeline_json.py

pipeline-datastore-view-rules:
	$(eval PB_TOOL_CONTRACT_DIR := `readlink -f registered-tool-contracts`)
	$(eval PB_PIPELINE_TEMPLATE_DIR := `readlink -f resolved-pipeline-templates`)
	PB_TOOL_CONTRACT_DIR=$(PB_TOOL_CONTRACT_DIR) \
		PB_PIPELINE_TEMPLATE_DIR=$(PB_PIPELINE_TEMPLATE_DIR) \
		python pb_pipeline_view_rules.py --output-dir pipeline-datastore-view-rules

report-view-rules:
	$(eval BASEDIR = $(shell python -c 'import pbreports.report; import os.path ; print os.path.dirname(pbreports.report.__file__)'))
	$(eval JSON = $(shell find $(BASEDIR) -type f -name '*.json'))
	@for j in $(JSON); do \
		cp $$j report-view-rules/ ;\
	done

tool-contracts:
	python regenerate_tool_contracts.py

manifests:
	python bin/generate-manifests.py version.txt

bundle: pipeline-template-json pipeline-datastore-view-rules report-view-rules manifests show-workflow-options
	$(eval VERSION := `grep Version manifest.xml | sed "s/<[\/]*Version>//g; s/\ *//;"`)
	$(eval BASENAME := "pbpipeline-resources-$(VERSION)")
	rm -rf $(BASENAME)
	mkdir -p $(BASENAME)
	cp -r chunk_operators $(BASENAME)/
	cp -r pipeline-datastore-view-rules $(BASENAME)/
	cp -r pipeline-template-view-rules $(BASENAME)/
	cp -r registered-tool-contracts $(BASENAME)/
	cp -r report-view-rules $(BASENAME)/
	cp -r resolved-pipeline-templates $(BASENAME)
	cp -r resolved-pipeline-template-presets $(BASENAME)/
	cp workflow_options.txt $(BASENAME)/
	cp manifest.xml $(BASENAME)/
	cp pacbio-manifest.json $(BASENAME)/
	tar -czf $(BASENAME).tar.gz $(BASENAME)
	@echo Bundle written to $(BASENAME).tar.gz
