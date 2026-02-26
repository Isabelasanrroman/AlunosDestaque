from flask import Flask, render_template, request, redirect, url_for, session
import csv
from collections import defaultdict
import psycopg2

app = Flask(__name__)
app.secret_key = "chave_secreta"

def conectar():
    return psycopg2.connect(
        host="localhost",
        database="alunosdestaques",
        user="postgres",
        password="1234"
    )

# -------------------- INDEX --------------------

@app.route('/')
def index():
    return render_template('index.html')


# -------------------- CADASTRO PROFESSOR --------------------

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO professor (nome, email, senha)
            VALUES (%s, %s, %s)
        """, (nome, email, senha))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('entrar'))

    return render_template('cadastrar.html')


# -------------------- LOGIN --------------------

@app.route('/entrar', methods=['GET', 'POST'])
def entrar():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            SELECT id_professor FROM professor
            WHERE email = %s AND senha = %s
        """, (email, senha))

        professor = cur.fetchone()

        cur.close()
        conn.close()

        if professor:
            session['id_professor'] = professor[0]
            return redirect(url_for('cursos_cadastrados'))
        else:
            return "Email ou senha incorretos"

    return render_template('entrar.html')


# -------------------- CADASTRAR TURMA + CSV --------------------

@app.route('/cadastrar-turmas', methods=['GET', 'POST'])
def cadastrar_turmas():
    # 🔹 Verificar se professor está logado
    if 'id_professor' not in session:
        return redirect(url_for('entrar'))

    if request.method == 'POST':
        nome_turma = request.form['turma']
        arquivo = request.files['arquivo']

        conn = conectar()
        cur = conn.cursor()

        # Criar turma
        cur.execute("""
            INSERT INTO turma (nome_turma, id_curso, id_professor)
            VALUES (%s, %s, %s)
            RETURNING id_turma
        """, (nome_turma, 1, session['id_professor']))

        id_turma = cur.fetchone()[0]

        dados = defaultdict(lambda: {"notas": [], "freqs": [], "disciplinas": []})

        conteudo = arquivo.stream.read()

        try:
            linhas = conteudo.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            linhas = conteudo.decode("latin-1").splitlines()

        leitor = csv.DictReader(linhas)

        for linha in leitor:
            nome = linha.get('nome') or linha.get('Nome') or linha.get('NOME')
            disciplina = linha.get('disciplina') or linha.get('Disciplina')

            # 🔹 PULAR LINHA SE NOME OU DISCIPLINA FOR VAZIO
            if not nome or not disciplina:
                continue

            nota = float(linha.get('nota') or linha.get('Nota') or 0)
            freq = float(
                linha.get('frequencia') 
                or linha.get('frequência') 
                or linha.get('Frequência') 
                or 0
            )

            dados[nome]["notas"].append(nota)
            dados[nome]["freqs"].append(freq)
            dados[nome]["disciplinas"].append((disciplina, nota, freq))

        alunos_lista = []

        for nome, info in dados.items():
            print("Tentando inserir aluno:", nome)
            if not nome:
                print("Nome vazio detectado, pulando linha")
                continue
            media = round(sum(info["notas"]) / len(info["notas"]), 2)
            freq_media = round(sum(info["freqs"]) / len(info["freqs"]), 2)

            if media >= 95 and freq_media == 100:
                classificacao = "🥇 Ouro"
            elif media >= 95 and freq_media >= 97:
                classificacao = "🥈 Prata"
            elif media >= 95 and freq_media >= 95:
                classificacao = "🥉 Bronze"
            else:
                classificacao = "—"

            # Inserir aluno
            cur.execute("""
                INSERT INTO aluno (nome, id_turma)
                VALUES (%s, %s)
                RETURNING id_aluno
            """, (nome, id_turma))

            id_aluno = cur.fetchone()[0]

            # Inserir boletim
            cur.execute("""
                INSERT INTO boletim (id_aluno, media_geral, frequencia_geral, classificacao)
                VALUES (%s, %s, %s, %s)
                RETURNING id_boletim
            """, (id_aluno, media, freq_media, classificacao))

            id_boletim = cur.fetchone()[0]

            # Inserir notas
            for disciplina, nota, freq in info["disciplinas"]:
                cur.execute("""
                    INSERT INTO nota (id_boletim, disciplina, nota, frequencia)
                    VALUES (%s, %s, %s, %s)
                """, (id_boletim, disciplina, nota, freq))

            alunos_lista.append({
                "nome": nome,
                "media": media,
                "freq": freq_media,
                "classificacao": classificacao
            })

        conn.commit()
        cur.close()
        conn.close()

        alunos_lista.sort(key=lambda x: (x["media"], x["freq"]), reverse=True)

        # 🔹 Redirecionar para página de classificação via rota, melhor consistência
        # return render_template("classificacao.html", alunos=alunos_lista, turma=nome_turma)
        return redirect(url_for('classificacao', id_turma=id_turma))

    return render_template("cadastrarturmas.html")


# -------------------- LISTAR TURMAS --------------------

@app.route('/cursos-cadastrados')
def cursos_cadastrados():
    if 'id_professor' not in session:
        return redirect(url_for('entrar'))

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT id_turma, nome_turma
        FROM turma
        WHERE id_professor = %s
    """, (session['id_professor'],))

    turmas = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('cursoscadastrados.html', turmas=turmas)


# -------------------- CLASSIFICAÇÃO --------------------
@app.route('/classificacao/<int:id_turma>')
def classificacao(id_turma):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT a.nome, b.media_geral, b.frequencia_geral, b.classificacao
        FROM aluno a
        JOIN boletim b ON a.id_aluno = b.id_aluno
        WHERE a.id_turma = %s
        ORDER BY b.media_geral DESC, b.frequencia_geral DESC
    """, (id_turma,))

    alunos = cur.fetchall()

    print("ID turma recebido:", id_turma)
    print("Alunos encontrados:", alunos)

    cur.close()
    conn.close()

    alunos_lista = []

    for a in alunos:
        alunos_lista.append({
            "nome": a[0],
            "media": float(a[1]),
            "freq": float(a[2]),
            "classificacao": a[3]
        })

    return render_template('classificacao.html', alunos=alunos_lista)

if __name__ == '__main__':
    app.run(debug=True)