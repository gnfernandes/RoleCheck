import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.cloud import storage
import os

# Configurações Iniciais
TOKEN = '6621746807:AAGZfLtnH-e8KOObiBT48atMKTnLSRtqusE'  # Substitua pelo seu token de bot
bot = telebot.TeleBot(TOKEN)

# Certifique-se de que a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS esteja configurada com o caminho do arquivo de credenciais
gcs_client = storage.Client()
bucket_name = 'my--credentials-sheets' 
credentials_filename = 'my-google-credentials.json'
local_credentials_path = '/tmp/' + credentials_filename

# Baixar o arquivo de credenciais do GCS para o ambiente local
bucket = gcs_client.get_bucket(bucket_name)
blob = bucket.blob(credentials_filename)
blob.download_to_filename(local_credentials_path)

# Autenticação com Google Sheets usando o arquivo de credenciais baixado
json_key_file = local_credentials_path
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1lBtyDZFFWggE9tego1tv386yUt-tWsd6p29tHL5qwpo/edit#gid=0').sheet1

# Dicionário para armazenar o estado da conversa e os dados coletados
user_data = {}

# Iniciar a conversa
@bot.message_handler(commands=['start'])
def start_conversation(message):
    chat_id = message.chat.id
    user_data[chat_id] = {
        'action': '',
        'category': '',
        'name': '',
        'address': '',
        'link': '',
        'visited': '',
        'experience': '',
        'rating': '',
        'edit_field': '',
        'edit_value': ''
    }
    welcome_message = (
        "Olá! 🎉 Seja bem-vindo ao nosso super bot de gerenciamento de locais! 🌍\n\n"
        "Aqui você pode adicionar informações sobre novos lugares ou editar informações existentes. "
        "Basta responder com 'novo' para adicionar, 'editar' para editar ou 'listar' para ver a lista de lugares. 📝\n\n"
        "E se em algum momento quiser cancelar o que está fazendo, é só digitar 'cancelar'. Simples assim! 😉\n\n"
        "Vamos começar? Escolha 'novo', 'editar' ou 'listar' para prosseguir!"
    )
    bot.send_message(chat_id, welcome_message)

# Função para listar os nomes dos lugares
def list_places():
    records = sheet.get_all_records()
    return [str(record['NamePlace']) for record in records]

# Função para converter a nota numérica em emojis de estrelas
def rating_to_stars(rating):
    try:
        rating = int(rating)
    except ValueError:
        return "Sem avaliação"
    if rating < 1 or rating > 5:
        return "Avaliação Inválida"
    return '⭐' * rating

# Função para listar informações resumidas dos lugares
def list_places_summary(chat_id):
    records = sheet.get_all_records()
    place_summary = [
        "Nome: {}\nCategoria: {}\nEndereço: {}\nLink: {}\nNota: {}\n".format(
            record['NamePlace'],
            record['Category'],
            record['Address'],
            record['Link'],
            rating_to_stars(record['Score'])
        ) for record in records
    ]
    bot.send_message(chat_id, "\n".join(place_summary) + "\nLink da Planilha: https://docs.google.com/spreadsheets/d/1lBtyDZFFWggE9tego1tv386yUt-tWsd6p29tHL5qwpo/edit#gid=0")

# Função para encontrar a linha do lugar escolhido
def find_row_by_place_name(place_name):
    records = sheet.get_all_records()
    for i, record in enumerate(records):
        if record['NamePlace'] == place_name:
            return i + 2

# Função para cancelar a conversa
def cancel_conversation(chat_id):
    bot.send_message(chat_id, "Conversa cancelada. Até a próxima!")
    if chat_id in user_data:
        del user_data[chat_id]

# Responder às mensagens
@bot.message_handler(func=lambda message: True)
def collect_info(message):
    chat_id = message.chat.id

    # Verificar se o usuário deseja cancelar a conversa
    if message.text.lower() == 'cancelar':
        cancel_conversation(chat_id)
        return

    if chat_id not in user_data:
        bot.send_message(chat_id, "Por favor, use o comando /start para iniciar.")
        return

    # Determinar ação do usuário
    if user_data[chat_id]['action'] == '':
        if message.text.lower() in ['novo', 'editar', 'listar']:
            user_data[chat_id]['action'] = message.text.lower()
            if message.text.lower() == 'novo':
                bot.send_message(chat_id, "Qual é a categoria?")
            elif message.text.lower() == 'editar':
                places = list_places()
                bot.send_message(chat_id, "Escolha um lugar para editar: \n" + '\n'.join(places))
                user_data[chat_id]['action'] = 'selecionar_lugar'
            elif message.text.lower() == 'listar':
                list_places_summary(chat_id)
                del user_data[chat_id]
        else:
            bot.send_message(chat_id, "Resposta inválida. Por favor, responda com 'novo', 'editar' ou 'listar'.")


    # Selecionar lugar para editar
    elif user_data[chat_id]['action'] == 'selecionar_lugar':
        if message.text in list_places():
            user_data[chat_id]['name'] = message.text
            bot.send_message(chat_id, "Qual campo você gostaria de editar? (Opções: 'Categoria', Nome, 'Endereço', 'Link', 'Visitado', 'Experiência', 'Nota')")
            user_data[chat_id]['action'] = 'editar_campo'
        else:
            bot.send_message(chat_id, "NamePlace não encontrado. Por favor, escolha um lugar da lista.")

# Continuação do seu código...

    # Editar campo específico
    elif user_data[chat_id]['action'] == 'editar_campo':
        if message.text in ['Categoria', 'Nome', 'Endereço', 'Link', 'Visitado', 'Experiência', 'Nota']:
            user_data[chat_id]['edit_field'] = message.text
            bot.send_message(chat_id, f"Por favor, forneça o novo valor para {message.text}.")
            user_data[chat_id]['action'] = 'atualizar_campo'
        else:
            bot.send_message(chat_id, "Campo inválido. Por favor, escolha entre 'Categoria', 'Nome', 'Endereço', 'Link', 'Visitado', 'Experiência', 'Nota'.")

    # Atualizar campo
    elif user_data[chat_id]['action'] == 'atualizar_campo':
        new_value = message.text
        field_mapping = {
            'Categoria': 'C',
            'Nome': 'D',  # Adicionado mapeamento para 'NamePlace'
            'Endereço': 'E',
            'Link': 'F',
            'Visitado': 'G',
            'Experiência': 'H',
            'Nota': 'I'
        }
        column_letter = field_mapping.get(user_data[chat_id]['edit_field'])
        if column_letter:
            row_number = find_row_by_place_name(user_data[chat_id]['name'])
            if row_number:
                # Atualizar 'NamePlace' precisa de um tratamento especial para evitar duplicatas
                if user_data[chat_id]['edit_field'] == 'NamePlace':
                    # Verificar se o novo nome já existe
                    if new_value in list_places():
                        bot.send_message(chat_id, "Erro: Já existe um lugar com esse nome.")
                        del user_data[chat_id]
                        return
                    else:
                        # Atualizar o nome do lugar na planilha
                        sheet.update_acell(f"{column_letter}{row_number}", new_value)
                        bot.send_message(chat_id, "Nome do lugar atualizado com sucesso!")
                else:
                    # Atualizar outros campos
                    sheet.update_acell(f"{column_letter}{row_number}", new_value)
                    bot.send_message(chat_id, "Informação atualizada com sucesso!")
            else:
                bot.send_message(chat_id, "Erro ao atualizar a informação.")
        else:
            bot.send_message(chat_id, "Campo inválido. Por favor, escolha um campo válido para editar.")
        del user_data[chat_id]

    # Restante do código...


    # Adicionar uma nova linha
    elif user_data[chat_id]['action'] == 'novo':
        if user_data[chat_id]['category'] == '':
            user_data[chat_id]['category'] = message.text
            bot.send_message(chat_id, "Qual é o NamePlace?")
        elif user_data[chat_id]['name'] == '':
            user_data[chat_id]['name'] = message.text
            bot.send_message(chat_id, "Qual é o endereço?")
        elif user_data[chat_id]['address'] == '':
            user_data[chat_id]['address'] = message.text
            bot.send_message(chat_id, "Por favor, envie o link.")
        elif user_data[chat_id]['link'] == '':
            user_data[chat_id]['link'] = message.text
            bot.send_message(chat_id, "Você visitou esse lugar? (Responda com 'sim' ou 'não')")
        elif user_data[chat_id]['visited'] == '':
            user_data[chat_id]['visited'] = message.text
            if message.text.lower() == 'sim':
                bot.send_message(chat_id, "Como foi a sua experiência?")
                user_data[chat_id]['action'] = 'coletar_experiencia'
            else:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                user_name = message.from_user.first_name + " " + message.from_user.last_name if message.from_user.last_name else message.from_user.first_name
                sheet.append_row([
                    timestamp, user_name, user_data[chat_id]['category'], user_data[chat_id]['name'],
                    user_data[chat_id]['address'], user_data[chat_id]['link'],
                    user_data[chat_id]['visited'], '', ''  # Experiência e nota ficam em branco
                ])
                bot.send_message(chat_id, "Informações adicionadas à planilha. Obrigado!")
                del user_data[chat_id]

    # Coletar experiência e nota se o usuário visitou o lugar
    elif user_data[chat_id]['action'] == 'coletar_experiencia':
        user_data[chat_id]['experience'] = message.text
        bot.send_message(chat_id, "Qual nota você dá para o lugar? (1-5)")
        user_data[chat_id]['action'] = 'coletar_nota'
    elif user_data[chat_id]['action'] == 'coletar_nota':
        user_data[chat_id]['rating'] = message.text
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_name = message.from_user.first_name + " " + message.from_user.last_name if message.from_user.last_name else message.from_user.first_name
        sheet.append_row([
            timestamp, user_name, user_data[chat_id]['category'], user_data[chat_id]['name'],
            user_data[chat_id]['address'], user_data[chat_id]['link'],
            user_data[chat_id]['visited'], user_data[chat_id]['experience'],
            user_data[chat_id]['rating']
        ])
        bot.send_message(chat_id, "Informações adicionadas à planilha. Obrigado!")
        del user_data[chat_id]

bot.polling(none_stop=True, timeout=123)


