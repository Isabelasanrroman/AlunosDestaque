
    const inputArquivo = document.getElementById("arquivo");
    const nomeArquivo = document.getElementById("nomeArquivo");

    inputArquivo.addEventListener("change", function() {
        if (inputArquivo.files.length > 0) {
            nomeArquivo.textContent = "Arquivo selecionado: " + inputArquivo.files[0].name;
        }
    });
