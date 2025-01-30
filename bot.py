import magic
from telegram import Update, Contact
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup


client = MongoClient("mongodb+srv://user1:areeba@cluster0.mongodb.net/sample_mflix?retryWrites=true&w=majority")
db = client['telegram_bot']
users_collection = db['users']


gemini_api_key = "AIzaSyC4cHP6jhWZIKKyULjyrUthMONRclXc4nc"


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Welcome! Please share your phone number.')
    update.message.reply_contact()


def save_contact(update: Update, context: CallbackContext) -> None:
    contact: Contact = update.message.contact
    user_info = {
        "first_name": update.message.from_user.first_name,
        "username": update.message.from_user.username,
        "chat_id": update.message.chat_id,
        "phone_number": contact.phone_number
    }
    users_collection.insert_one(user_info)
    update.message.reply_text('Thank you! Your phone number has been saved.')


def handle_query(update: Update, context: CallbackContext) -> None:
    user_query = update.message.text
    chat_id = update.message.chat_id

    
    response = requests.post(
        'https://api.gemini.com/v1/query',
        headers={'Authorization': 'Bearer AIzaSyC4cHP6jhWZIKKyULjyrUthMONRclXc4nc'},
        json={'query': user_query}
    )
    gemini_response = response.json()

    
    chat_history = {
        "chat_id": chat_id,
        "user_query": user_query,
        "bot_response": gemini_response.get('answer', 'No answer available.'),
        "timestamp": update.message.date
    }
    users_collection.update_one(
        {"chat_id": chat_id},
        {"$push": {"chat_history": chat_history}}
    )

    update.message.reply_text(gemini_response.get('answer', 'No answer available.'))


def gemini_file_analysis(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            'https://api.gemini.com/v1/analyze',
            headers={'Authorization': 'Bearer AIzaSyC4cHP6jhWZIKKyULjyrUthMONRclXc4nc'},
            files=files
        )
    response_data = response.json()
    return response_data.get('description', 'No description available.')


def handle_file(update: Update, context: CallbackContext) -> None:
    file = update.message.document or update.message.photo[-1].get_file()
    file_path = file.download('temp_file')

    file_type = magic.from_file(file_path, mime=True)
    file_description = gemini_file_analysis(file_path)  

    file_info = {
        "filename": file.file_name if update.message.document else file.file_unique_id,
        "description": file_description,
        "file_type": file_type
    }
    users_collection.update_one(
        {"chat_id": update.message.chat_id},
        {"$push": {"files": file_info}}
    )

    update.message.reply_text(f'File analyzed: {file_description}')


def web_search(query):
    response = requests.get(f"https://www.bing.com/search?q={query}")
    soup = BeautifulSoup(response.text, "html.parser")

    search_results = []
    for result in soup.find_all("li", class_="b_algo"):
        title = result.find("a").text
        link = result.find("a")["href"]
        snippet = result.find("p").text
        search_results.append({"title": title, "link": link, "snippet": snippet})

    return search_results


def websearch(update: Update, context: CallbackContext) -> None:
    user_query = ' '.join(context.args)
    search_results = web_search(user_query)
    
    if not search_results:
        update.message.reply_text("No results found.")
    else:
        for result in search_results[:3]:  
            update.message.reply_text(f"{result['title']}\n{result['snippet']}\n{result['link']}")


updater = Updater("7679932208:AAHWrXbEcF_XJ8cuQx0wTdC40wMq5hC_aIk", use_context=True)
dp = updater.dispatcher


dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.contact, save_contact))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_query))
dp.add_handler(MessageHandler(Filters.document | Filters.photo, handle_file))
dp.add_handler(CommandHandler("websearch", websearch))


updater.start_polling()
updater.idle()
