# TravelPipa — site da agência boutique de turismo

Site multilíngue (inglês, português e espanhol) da **TravelPipa**, em Praia da Pipa (RN): catálogo de experiências e transfers, solicitações de reserva, painel administrativo e SEO técnico.

**Slogan:** Discover Pipa. Experience More.

Stack: Python 3.13 · Django 5.2 · Django Templates · Bootstrap 5 · PostgreSQL (produção) / SQLite (desenvolvimento) · WhiteNoise · Gunicorn.

---

## Sumário

1. [Instalação e execução local](#1-instalação-e-execução-local)
2. [Estrutura do projeto](#2-estrutura-do-projeto)
3. [Gestão TravelPipa (área administrativa)](#3-gestão-travelpipa-área-administrativa)
4. [Idiomas e traduções](#4-idiomas-e-traduções)
5. [Reservas e notificações](#5-reservas-e-notificações)
6. [SEO](#6-seo) · [Maré e tempo](#61-maré-e-tempo)
7. [Segurança e LGPD](#7-segurança-e-lgpd)
8. [Testes](#8-testes)
9. [Publicação no Railway com travelpipa.com.br](#9-publicação-no-railway-com-travelpipacombr)
10. [Deploy em servidor Linux (alternativa)](#10-deploy-em-servidor-linux-alternativa)
11. [Antes de publicar — checklist](#11-antes-de-publicar--checklist)
12. [Próximas versões](#12-próximas-versões)

---

## 1. Instalação e execução local

Pré-requisitos: Python 3.12 ou 3.13.

```bash
# 1. Ambiente virtual
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. Dependências
pip install -r requirements.txt

# 3. Variáveis de ambiente
cp .env.example .env                 # edite SECRET_KEY e mantenha DEBUG=True

# 4. Banco de dados (SQLite em desenvolvimento)
python manage.py migrate

# 5. Passeios reais (lancha, jeep, Guaraíras e quadriciclo), com fotos e vídeo da pasta content/
python manage.py load_tours
#    (use --replace-media para substituir fotos/vídeo desses passeios pelos arquivos da pasta content/)

#    Conteúdo de demonstração (opcional, marcado como "Demo" no site)
python manage.py seed_demo
#   --with-demo-contact  preenche um WhatsApp fictício só para visualizar os botões
#   --remove             apaga as experiências de demonstração

# 6. Usuário administrador
python manage.py createsuperuser

# 7. Servidor
python manage.py runserver
```

- Site: <http://localhost:8000/> (redireciona para `/en/`, `/pt-br/` ou `/es/`)
- Gestão TravelPipa: <http://localhost:8000/gestao/> (painel da equipe)
- Painel técnico do Django: <http://localhost:8000/painel/> (`ADMIN_URL`)

Gerar uma SECRET_KEY:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

---

## 2. Estrutura do projeto

```
travelpipa/
├── config/                 # settings, urls, wsgi
├── core/                   # SiteSettings, Testimonial, ContactMessage
│   ├── i18n.py             # campos multilíngues (title_en / title_pt / title_es)
│   ├── seo.py              # canonical, hreflang, dados estruturados (JSON-LD)
│   ├── antispam.py         # honeypot, tempo mínimo e limite por IP
│   ├── images.py           # redimensionamento automático das fotos enviadas
│   ├── sitemaps.py         # sitemap.xml com alternativas por idioma
│   ├── management/commands/seed_demo.py
│   └── tests.py            # testes automatizados (76 testes)
├── tours/                  # Category, Experience, ExperienceImage
├── bookings/               # BookingRequest, formulário e notificações por e-mail
├── templates/              # Django Templates (base, includes, páginas)
├── static/
│   ├── css/travelpipa.css  # identidade visual
│   ├── js/travelpipa.js    # melhorias progressivas (o site funciona sem JS)
│   ├── img/                # favicon e imagens de demonstração
│   └── vendor/             # Bootstrap, Bootstrap Icons e fontes (hospedados localmente)
├── locale/                 # traduções pt_BR e es (.po e .mo compilados)
├── content/                # fotos e vídeos reais enviados pela TravelPipa (usados pelo load_tours)
├── media/                  # fotos enviadas pelo painel (MEDIA_ROOT)
├── bin/start.sh            # collectstatic + migrate + gunicorn
├── railpack.json           # comando de início no Railway
├── Procfile                # alternativa para outras plataformas
├── requirements.txt
└── .env.example
```

### Modelos

| Modelo | Para que serve |
|---|---|
| `Category` | Categorias (nome/descrição nos 3 idiomas, imagem, ícone, ordem, ativa). `is_transfer` marca a categoria cujos itens aparecem em **Transfers**. |
| `Experience` | Passeios e transfers: textos nos 3 idiomas, preço opcional, duração, itinerário, incluído/não incluído, informações importantes, política de cancelamento, SEO, destaque, ordem, ativa, origem/destino/modalidade/capacidade (transfers). |
| `ExperienceImage` | Galeria de fotos, com texto alternativo nos 3 idiomas e foto de capa. |
| `BookingRequest` | Solicitação de reserva: código `TP-XXXXXXX`, UUID, status, observações internas, data do consentimento LGPD. |
| `Testimonial` | Somente avaliações reais. Só aparecem se marcadas como **reais** e **publicadas**, e somente no idioma em que foram escritas. Sem depoimentos, a seção fica oculta. |
| `SiteSettings` | Registro único com logotipo, fotos, WhatsApp, e-mail, redes sociais, endereço, textos institucionais e páginas legais. |
| `ContactMessage` | Mensagens do formulário de contato. |

Todos têm `created_at` e `updated_at`.

---

## 3. Gestão TravelPipa (área administrativa)

A equipe usa a **Gestão TravelPipa**, um painel próprio com o visual do site, em português e pensado para usar no celular:

- Endereço: `https://seu-dominio/gestao/` (configurável em `PANEL_URL`).
- Acesso: usuários com permissão de equipe (*staff*). Para criar o primeiro: `python manage.py createsuperuser`.
- Segurança: depois de 5 senhas erradas, o acesso daquele usuário naquele aparelho fica bloqueado por 15 minutos (`PANEL_LOGIN_MAX_ATTEMPTS`, `PANEL_LOGIN_LOCK_MINUTES`). Todas as ações exigem login e proteção CSRF; as páginas não aparecem no Google.

| Tela | O que dá para fazer |
|---|---|
| **Início** | Reservas pendentes, próximas reservas, mensagens sem resposta, aviso de passeios de demonstração |
| **Passeios** | Ligar/desligar (ativo no site) e destaque com um toque; buscar e filtrar; criar, editar e excluir |
| **Editar passeio** | Textos em abas PT/EN/ES, preço, transfer, vídeo, selos (maré, guia com Cadastur), SEO |
| **Fotos** | Enviar várias de uma vez, escolher a capa (estrela), reordenar (arrastar ou setas), editar a descrição, excluir. A qualidade original é mantida |
| **Categorias** | Ligar/desligar e editar nomes nos 3 idiomas |
| **Reservas** | Filtrar por status, buscar, ver dados do cliente, botão de WhatsApp com mensagem pronta no idioma do cliente, mudar status e anotar observações internas |
| **Mensagens** | Ler e marcar como respondida |
| **Depoimentos** | Cadastrar apenas avaliações reais (só aparecem se marcadas como reais e publicadas) |
| **Configurações do site** | WhatsApp, e-mail, redes, endereço, fotos do banner e da seção "A região", logotipo, selos de confiança, textos institucionais e páginas legais |

O painel técnico do Django continua em `/painel/` (`ADMIN_URL`), apenas para tarefas técnicas, como criar usuários e dar permissões.

**Dicas:**
- Slug pode ficar vazio: é gerado a partir do título em inglês.
- Preço vazio = "Preço sob consulta".
- Listas (incluído, roteiro etc.) usam **um item por linha**.
- Campos em português e espanhol vazios usam o texto em inglês.

## 4. Idiomas e traduções

- URLs por idioma, com caminhos traduzidos:
  - `/en/experiences/` · `/pt-br/passeios/` · `/es/experiencias/`
  - `/en/transfers/` · `/pt-br/transfers/` · `/es/traslados/`
  - `/en/book/` · `/pt-br/reservar/` · `/es/reservar/`
- O seletor de idioma mantém a mesma página e grava a preferência em um cookie (`travelpipa_lang`). Ao acessar `/`, o visitante vai para o idioma escolhido antes (ou o do navegador).
- Textos fixos (menus, botões, formulários, erros, páginas legais) estão em `locale/`. Para alterar:

```bash
python manage.py makemessages -l pt_BR -l es      # requer GNU gettext
# edite locale/pt_BR/LC_MESSAGES/django.po e locale/es/LC_MESSAGES/django.po
python manage.py compilemessages
```

Os arquivos `.mo` compilados já estão no projeto, então o servidor não precisa do gettext.

---

## 5. Reservas e notificações

1. O visitante escolhe a experiência (ou chega pelo botão “Request a Booking” da página do passeio, que já pré-seleciona a experiência).
2. Informa data, número de pessoas, nome, e-mail, WhatsApp/telefone, idioma de atendimento, observações e aceita o consentimento LGPD.
3. A solicitação é salva com código único `TP-XXXXXXX`, status **Pendente**, data e horário.
4. A página de confirmação mostra o código e deixa claro que **a reserva ainda não está confirmada**. Nenhum pagamento é processado.
5. Com o e-mail configurado (`RESEND_API_KEY`, ou `EMAIL_HOST` em servidores que permitem SMTP), a equipe recebe um aviso com os dados e o link para o painel. **Responder esse e-mail responde direto para o cliente.** Os destinatários vêm de `NOTIFICATION_EMAILS` ou, se vazio, do e-mail das configurações do site. Configuração na seção 9.4.

Os botões de WhatsApp usam o número das configurações do site e já levam uma mensagem com o nome e o link da experiência.

---

## 6. SEO

- `<title>` e meta description por página e idioma (experiências têm campos de SEO próprios, opcionais).
- `canonical`, `hreflang` (en, pt-br, es e x-default) e Open Graph.
- `/sitemap.xml` com todas as páginas nos três idiomas e alternativas `hreflang`.
- `/robots.txt` apontando para o sitemap.
- Dados estruturados (JSON-LD): `TravelAgency` na página inicial, `TouristTrip` e `BreadcrumbList` nas experiências. Usam apenas dados preenchidos no painel; a oferta de preço só é publicada quando há preço real. Conteúdo de demonstração recebe `noindex` e não gera dados estruturados.
- Imagens com `loading="lazy"` e dimensões declaradas, mantidas na qualidade original; fontes, CSS e ícones servidos localmente com cache longo (WhiteNoise).

Defina `SITE_URL` com o domínio final (ex.: `https://travelpipa.com.br`) para canonical e sitemap corretos.

---

## 6.1 Maré e tempo

Página **Maré e tempo** (`/pt-br/mare-e-tempo/`, `/en/tides-and-weather/`, `/es/mareas-y-clima/`), faixa de condições na página inicial e quadro "Melhor na maré baixa" nos passeios marcados como **depende da maré baixa** no painel.

| Dado | Fonte | Custo |
|---|---|---|
| Tempo agora e previsão de 6 dias | [MET Norway](https://api.met.no/) (instituto meteorológico oficial da Noruega, cobertura mundial) | Gratuito, uso comercial permitido (CC BY 4.0) |
| Nascer e pôr do sol | Calculado pelo próprio site | — |
| Tábua de marés (7 dias) | [Tábua de Maré API](https://tabuamare.api.br/) — previsão oficial da Marinha (DHN) para o porto de Natal | Gratuito. Funciona sem chave; com a chave gratuita, o site tem cota própria (32 mil consultas/mês) e usa cerca de 120 por mês |

- **Marés funcionam sem configurar nada.** Recomendado: crie a conta gratuita em [tabuamare.api.br](https://tabuamare.api.br/) (login com Google) e preencha `TABUAMARE_API_KEY`. Sem chave, o limite é dividido com outros sites que saem pelo mesmo IP do servidor.
- A Tábua de Maré API é um projeto independente, sem garantia de funcionamento. Se ela ficar fora do ar, o site mostra os últimos dados válidos e, depois de 3 dias, um link para as [tábuas oficiais da Marinha](https://www.marinha.mil.br/chm/tabuas-de-mare).
- Alternativa paga: `TIDES_PROVIDER=worldtides` com `WORLDTIDES_API_KEY` ([WorldTides](https://www.worldtides.info/developer), a partir de US$ 7,49/mês).
- Preencha também `WEATHER_CONTACT` com o e-mail ou site da agência (exigência da MET Norway).
- Os dados ficam em cache (tempo: 30 min; marés: 12 h). Se um serviço sair do ar, o site continua mostrando os últimos dados válidos por até 3 dias e nunca fica lento ou com erro por causa disso. Na página inicial e nos passeios, os quadros carregam depois da página.
- O cache agora fica no banco de dados (tabela criada automaticamente pelo `migrate`). Isso também faz o limite anti-spam dos formulários valer para todos os processos do servidor.

## 7. Segurança e LGPD

- `SECRET_KEY` e credenciais apenas em variáveis de ambiente; o projeto não inicia em produção sem `SECRET_KEY`.
- Com `DEBUG=False`: HTTPS obrigatório, HSTS, cookies seguros, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Cross-Origin-Opener-Policy`.
- **Content-Security-Policy:** o navegador só executa scripts e carrega arquivos do próprio site, o que bloqueia código injetado. Também há **Permissions-Policy** (sem câmera, microfone ou localização).
- **Domínio único:** `www.`, `http://` e o endereço do Railway redirecionam (301) para `https://travelpipa.com.br`.
- CSRF em todos os formulários.
- Anti-spam sem serviços externos: campo isca (honeypot), tempo mínimo de preenchimento assinado e limite de envios por IP por hora. O IP é lido da última entrada confiável do `X-Forwarded-For`, então não dá para burlar o limite forjando o cabeçalho. Ele é guardado apenas como hash temporário.
- **Login do painel:** 5 tentativas erradas por IP e usuário bloqueiam por 15 minutos, e 20 por usuário, vindas de qualquer IP, também bloqueiam. O admin técnico do Django (`ADMIN_URL`) usa o mesmo login protegido. As sessões expiram em 3 dias. Senha mínima de 10 caracteres.
- **Arquivos enviados:** apenas fotos (validadas pelo Pillow) e vídeos MP4/WEBM. O servidor de mídia só entrega esses tipos, nunca HTML, SVG ou scripts.
- Avisos por e-mail com assunto limpo (sem quebras de linha), o que impede injeção de cabeçalhos.
- Erros 500 enviam um e-mail para `ERROR_EMAILS`.
- Dependências auditadas com `pip-audit`, sem vulnerabilidades conhecidas (Pillow atualizado para 13.0.0).
- Dados de clientes ficam só no painel; a página de confirmação não exibe dados pessoais.
- Consentimento LGPD obrigatório nos formulários, com data e hora registradas; política de privacidade editável.
- Apenas cookies essenciais (idioma, sessão e CSRF). Fontes e bibliotecas hospedadas localmente, sem chamadas a terceiros no navegador.

---

## 8. Testes

```bash
python manage.py test
```

Os 119 testes cobrem: páginas nos três idiomas, URLs traduzidas, troca e persistência de idioma, filtros, experiências inativas, preços, SEO (canonical, hreflang, sitemap, JSON-LD), fluxo de reserva completo, validações, anti-spam, CSRF, limite de envios, notificação por e-mail, formulário de contato, segurança (IP real, bloqueio de login, redirecionamento de domínio, cabeçalhos, mídia, e-mail), painel (cadastro e edição de experiência com foto, alteração de status, ações em massa) e o comando de demonstração. Também foram executados contra PostgreSQL 16.

---

## 9. Publicação no Railway com travelpipa.com.br

### 9.1 Projeto e banco
1. Envie o projeto para um repositório **privado** no GitHub (o `.gitignore` já deixa de fora `.env`, banco local e `media/`; a pasta `content/` com as fotos originais **deve** ir junto).
2. No Railway: **New Project → Deploy from GitHub repo** e escolha o repositório.
3. No mesmo projeto: **+ Create → Database → PostgreSQL**.
4. No serviço do site: botão direito → **Attach Volume**, *mount path* `/data` (fotos e vídeos ficam aqui; sem volume eles somem a cada deploy).

### 9.2 Variáveis (aba Variables do serviço do site)

| Variável | Valor |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `SECRET_KEY` | chave longa e aleatória (comando na seção 1) |
| `DEBUG` | `False` |
| `SITE_URL` | `https://travelpipa.com.br` |
| `MEDIA_ROOT` | `/data/media` |
| `SERVE_MEDIA` | `True` |
| `ADMIN_URL` | caminho próprio para o admin técnico, ex.: `tp-admin-7x/` |
| `RESEND_API_KEY` | chave da Resend (seção 9.4) |
| `DEFAULT_FROM_EMAIL` | `TravelPipa <suporte@travelpipa.com.br>` |
| `NOTIFICATION_EMAILS` | `suporte@travelpipa.com.br` |
| `ERROR_EMAILS` | `suporte@travelpipa.com.br` |
| `WEATHER_CONTACT` | `suporte@travelpipa.com.br` |
| `TABUAMARE_API_KEY` | sua chave da Tábua de Maré |
| `DJANGO_SUPERUSER_USERNAME` | usuário do painel, ex.: `equipe` |
| `DJANGO_SUPERUSER_PASSWORD` | senha forte (apague esta variável depois do primeiro deploy) |
| `SECURE_HSTS_SECONDS` | `2592000` (30 dias); depois de 1–2 semanas sem problemas, `31536000` |

`ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` não precisam ser preenchidos: `SITE_URL` já libera `travelpipa.com.br` e `www.travelpipa.com.br`, e o Railway adiciona o próprio endereço.

**O que acontece em cada deploy** (`bin/start.sh`): `collectstatic`, `migrate` e `prepare_site`. No primeiro deploy (banco vazio), o `prepare_site` cadastra os passeios reais com fotos e vídeos, preenche o e-mail de contato e cria o usuário do painel. Nos deploys seguintes, ele não altera nada do que a equipe mudou no painel e apenas mostra no log uma lista do que ainda falta configurar.

### 9.3 Domínio
O `registro.br` não aceita apontar o domínio raiz (`travelpipa.com.br`, sem www) para o Railway, porque o Railway não fornece IP fixo. A solução recomendada pelo próprio Railway é usar o DNS gratuito da Cloudflare.

1. **Antes de mudar qualquer coisa:** no painel de DNS atual, anote todos os registros, principalmente **MX**, **TXT** (SPF/DKIM/DMARC) e **CNAME** do e-mail. São eles que fazem `suporte@travelpipa.com.br` funcionar.
2. Crie uma conta grátis em cloudflare.com → **Add a domain** → `travelpipa.com.br` → plano **Free**. A Cloudflare importa os registros existentes. **Confira que todos os registros do e-mail foram importados**; se faltar algum, crie manualmente.
3. No Railway: serviço do site → **Settings → Networking → Custom Domain** → adicione `travelpipa.com.br` e depois `www.travelpipa.com.br`. Para cada um, o Railway mostra um **CNAME** e um **TXT**.
4. Na Cloudflare (**DNS → Records**), crie os registros que o Railway mostrou:
   - `CNAME` nome `@` → destino do Railway, **proxy desligado (nuvem cinza, "DNS only")**
   - `CNAME` nome `www` → destino do Railway, **nuvem cinza**
   - os `TXT` de verificação, exatamente como o Railway mostrou
5. No **registro.br** → domínio → **DNS → Alterar servidores DNS** → coloque os dois servidores que a Cloudflare indicar.
6. Espere a propagação (minutos até algumas horas). O Railway emite o certificado HTTPS sozinho e marca o domínio como ativo.
7. Teste: `https://travelpipa.com.br` abre o site; `www.travelpipa.com.br` e o endereço `*.up.railway.app` redirecionam para ele. Envie e receba um e-mail em `suporte@` para confirmar que o e-mail continua funcionando.

> Se um dia ligar o proxy da Cloudflare (nuvem laranja), use SSL/TLS **Full** e defina `TRUSTED_PROXY_COUNT=2`.

> No plano **Trial** o Railway aceita só 1 domínio; no **Hobby**, 2 por serviço (raiz + www).

### 9.4 E-mails do site (avisos de reserva)
O Railway bloqueia o envio por SMTP nos planos Free, Trial e Hobby. Por isso, o site envia os avisos pela API HTTPS da **Resend**, que tem plano gratuito (3.000 e-mails por mês, até 100 por dia).

1. Crie a conta em resend.com → **Domains → Add Domain** → `travelpipa.com.br`.
2. A Resend mostra alguns registros (TXT/MX/CNAME) num **subdomínio próprio de envio**. Crie esses registros na Cloudflare. Eles não mexem no e-mail `suporte@`, que continua recebendo normalmente.
3. Depois que o domínio aparecer como verificado, crie uma **API Key** (permissão *Sending access*) e coloque em `RESEND_API_KEY`.
4. Faça uma solicitação de reserva de teste: o aviso chega em `suporte@`, e **responder o e-mail responde direto para o cliente**.

### 9.5 Depois de publicar
- Entre em `https://travelpipa.com.br/gestao/` com o usuário criado e preencha **Configurações**: WhatsApp, CNPJ, número Cadastur e redes sociais.
- Apague a variável `DJANGO_SUPERUSER_PASSWORD` no Railway.
- **Esqueceu a senha?** Crie de novo `DJANGO_SUPERUSER_USERNAME` e `DJANGO_SUPERUSER_PASSWORD` (com a nova senha) e faça um redeploy. O usuário recebe a nova senha e qualquer bloqueio por tentativas é liberado. Depois, apague a variável da senha outra vez.
- Cadastre o site no Google Search Console e envie `https://travelpipa.com.br/sitemap.xml`.
- **Health check (opcional):** em **Settings → Deploy → Healthcheck Path**, use `/healthz/`.

> **Observação:** o Railway marcou o antigo arquivo `railway.json` como obsoleto. Este projeto usa `railpack.json` e `Procfile`.

---

## 10. Deploy em servidor Linux (alternativa)

```bash
pip install -r requirements.txt
export DEBUG=False SECRET_KEY=... DATABASE_URL=postgres://... ALLOWED_HOSTS=... SITE_URL=https://...
sh bin/start.sh          # collectstatic + migrate + gunicorn em $PORT (padrão 8000)
```

Coloque o Gunicorn atrás de Nginx com HTTPS; o Nginx pode servir `/media/` diretamente (nesse caso, `SERVE_MEDIA=False`). Use systemd para manter o processo ativo.

---

## 11. Antes de publicar — checklist

O log de cada deploy mostra automaticamente o que ainda falta (comando `prepare_site`).

- [ ] Variáveis da seção 9.2 preenchidas, com `DEBUG=False` e uma `SECRET_KEY` nova
- [ ] Volume em `/data` e `MEDIA_ROOT=/data/media`
- [ ] Domínio ativo com HTTPS, e o e-mail `suporte@` testado depois da troca de DNS
- [ ] Resend verificada e reserva de teste recebida por e-mail
- [ ] WhatsApp, CNPJ e Cadastur preenchidos no painel (**Configurações**)
- [ ] Todo passeio ativo com foto e preço (ou desativado até ter)
- [ ] Política de privacidade e termos revisados
- [ ] `DJANGO_SUPERUSER_PASSWORD` apagada depois do primeiro deploy
- [ ] Sitemap enviado ao Google Search Console

---

## 12. Próximas versões

Fora do escopo deste MVP (pagamento online, disponibilidade automática, área do cliente, afiliados etc.). A arquitetura já facilita essas adições:

- **Pagamentos:** `BookingRequest` tem `uuid` e status próprios; um app `payments` pode se ligar a ele sem alterar o fluxo atual.
- **Disponibilidade / operadores:** um modelo `Operator` com FK em `Experience`.
- **Área do cliente:** o `uuid` da solicitação permite links de acompanhamento seguros.
- **Novos idiomas:** adicionar o idioma em `LANGUAGES`, o sufixo em `core/i18n.py` e os campos correspondentes.
