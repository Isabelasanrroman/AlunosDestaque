async function cadastrar() {

    let nome = document.getElementById("nome").value;
    let email = document.getElementById("email").value;
    let senha = document.getElementById("senha").value;

    await fetch("/api/cadastrar", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            nome: nome,
            email: email,
            senha: senha
        })

    });

    alert("Cadastrado com sucesso");

    window.location.href = "/";
}