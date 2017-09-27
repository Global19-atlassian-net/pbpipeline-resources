<?xml version="1.0" encoding="utf-8" ?>
<chunk-operator id="pbsmrtpipe.operators.chunk_pbtranscript2tools_cluster">

    <task-id>pbtranscript.tasks.ice_partial</task-id>

    <scatter>
        <scatter-task-id>pbtranscript2tools.tasks.scatter_cluster</scatter-task-id>
        <chunks>
            <chunk out="$chunk.json_id" in="pbtranscript2tools.tasks.cluster:0"/>
            <chunk out="$chunk.csv_id" in="pbtranscript2tools.tasks.cluster:1"/>
        </chunks>
    </scatter>
    <!-- Define the Gather Mechanism -->
    <gather>
        <chunks>
            <chunk>
                <gather-task-id>pbcoretools.tasks.gather_txt</gather-task-id>
                <chunk-key>$chunk.txt_id</chunk-key>
                <task-output>pbtranscript2tools.tasks.cluster</task-output>
            </chunk>
        </chunks>
    </gather>
</chunk-operator>
