function hash_process(event) {
    block_default_behavior(event);
    var files = event.dataTransfer ? event.dataTransfer.files : event.target.files; 
    var file = files[0];
    var fileType = file.type !== '' ? file.type : 'n/a';
    const fileSize = human_file_size(file.size);

    if(file.size > 0) {
        $("#results").show();
        $("#zone").hide();
        $("#filenameResult").append("<strong>" + file.name + "</strong>  ¦ " + fileSize + " (" + fileType + ")");
        $("#id_filename_value").val(file.name);
        var workers = [];

        var workerMD5 = new Worker(md5Path);
        workerMD5.addEventListener('message', workerResponse('md5_value'));
        workers.push(workerMD5);

        var workerSHA256 = new Worker(sha256Path);
        workerSHA256.addEventListener('message', workerResponse('sha256_value'));
        workers.push(workerSHA256);

        hash_file(file, workers);
    }
}

function block_default_behavior(event) {
    event.stopPropagation();
    event.preventDefault();
}

function human_file_size(size) {
    var i = size == 0 ? 0 : Math.floor( Math.log(size) / Math.log(1024) );
    return ( size / Math.pow(1024, i) ).toFixed(2) * 1 + ' ' + ['octets', 'Ko', 'Mo', 'Go', 'To'][i];
};

function workerResponse(id) {
    return function (event) {
        if (event.data.result) {
            $("#" + id).html(event.data.result);
            $("#id_"+id).val(event.data.result);
            $("#input_"+id).val(event.data.result);
            $('#sub').attr("disabled", false);
        } else {
            var percent = Math.round((((event.data.block.end * 100) / event.data.block.file_size) * 10) / 10);
            $("#progress_" + id).html(
                '<div class="progress" style="margin-bottom:0px"><div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="' + percent.toString() + '" aria-valuemin="0" aria-valuemax="100" style="width:' + percent.toString() + '%; text-align:left;">&nbsp;' + percent.toString() + '%</div></div>'
            );
        }
    };
}

function hash_file(file, workers) {
    var n = 0;
    var block = {
        'start': 0,
        'end': ((1048576 > file.size) ? file.size : 1048576),
        'file_size': file.size
    };
    for (var i = 0; i < workers.length; i += 1) {
        workers[i].addEventListener('message', blockHash);
    }
    var reader = new FileReader();
    reader.onload = blockLoad;
    var blob = file.slice(block.start, block.end);
    reader.readAsArrayBuffer(blob);

    function blockLoad(event) {
        for (var i = 0; i < workers.length; i += 1) {
            n += 1;
            workers[i].postMessage({
                'message': event.target.result,
                'block': block
            });
        }
    };

    function blockHash() {
        n -= 1;
        if (n === 0) {
            if (block.end !== file.size) {
                block.start += 1048576;
                block.end += 1048576;
                if (block.end > file.size) {
                    block.end = file.size;
                }
                var reader = new FileReader();
                reader.onload = blockLoad;
                var blob = file.slice(block.start, block.end);
                reader.readAsArrayBuffer(blob);
            }
        }
    };
}