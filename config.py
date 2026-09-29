# Configurações de busca do robô de vagas.

SEARCH_URLS = [
    # 1) Porto Alegre e região (presencial ou híbrido)
    "https://www.linkedin.com/jobs/search/?f_E=2%2C3&f_T=2490%2C25201%2C24%2C3172%2C848&f_TPR=r86400&geoId=90009578&keywords=desenvolvedor%20junior&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=R",
    # 2) Brasil todo, somente remotas
    "https://www.linkedin.com/jobs/search/?f_E=2%2C3&f_T=2490%2C25201%2C24%2C3172%2C848&f_TPR=r86400&f_WT=2&geoId=106057199&keywords=desenvolvedor%20junior&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R",
]

# Máximo de vagas por URL (controla o custo na Apify)
LIMIT_PER_SOURCE = 10

# --- Filtro por título ---
# A vaga só passa se o título tiver PELO MENOS UMA destas palavras:
TITULO_DEVE_TER = [
    "desenvolvedor", "desenvolvedora", "developer", "programador",
    "engenheiro de software", "software engineer",
    "full stack", "fullstack", "front end", "front-end", "frontend",
    "analista de dados", "analista de bi", "data analyst",
    "back end", "back-end", "backend", "mobile",
    "react", "java", "python", "react native",
]

# A vaga é descartada se o título tiver QUALQUER uma destas:
TITULO_NAO_PODE_TER = [
    # nível acima de júnior
    "sênior", "senior", "sr", "pleno", "pl", "especialista",
    "lead", "líder", "gerente", "manager", "coordenador",
    "arquiteto", "staff", "principal", "estágio", "estagio",
    # tecnologias que você não quer
    "salesforce", "sap", "abap", "protheus", "advpl", "cobol", "delphi", ".net", "php", "android",
    "go", "c#", "php", "ruby", "perl", "pascal", "fortran", 
]

# --- IA / Groq ---
MODELO_GROQ = "openai/gpt-oss-120b"  # modelo de LLM para avaliação das vagas
MAX_CARACTERES_DESCRICAO = 3000   # quanto da descrição da vaga vai para a IA
PAUSA_ENTRE_CHAMADAS = 8          # segundos de espera entre uma vaga e outra

# Nota mínima (0 a 100) para a vaga ir para o Telegram
NOTA_MINIMA = 40