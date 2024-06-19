from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, Message
import db
from time import sleep
from random import choice
import os

TOKEN = "7319533194:AAEAQTo954CQXaDgEqJ7K_HV953b_kl-6jI"

bot = TeleBot(TOKEN)

players = []

game = False
night = True

if not os.path.exists("db.db"):
    db.create_tables()


def get_killed(night:bool) -> str:
    if not night:
        username_killed = db.citizen_kill()
        return f"Горожане выгнали: {username_killed}"
    username_killed = db.mafia_kill()
    return f"Мафия убила: {username_killed}"

def autoplay_citizen(message: Message):
    players_roles = db.get_players_roles()
    for player_id, _ in players_roles:
        usernames = db.get_all_alive()
        name = f'robot{player_id}'
        if player_id < 5 and name in usernames:
            usernames.remove(name)
            vote_username = choice(usernames)
            db.vote('citizen_vote', vote_username, player_id)
            bot.send_message(message.chat.id, f'{name} проголосовал против {vote_username}')
            sleep(0.5)

def autoplay_mafia():
    players_roles = db.get_players_roles()
    for player_id, role in players_roles:
        usernames = db.get_all_alive()
        name = f'robot{player_id}'
        if player_id < 5 and name in usernames and role == 'mafia':
            usernames.remove(name)
            vote_username = choice(usernames)
            db.vote('mafia_vote', vote_username, player_id)

def game_llop(message: Message):
    global night, game
    bot.send_message(message.chat.id, "Добро пожаловать в игру! Вам даётся 2 минуты, чтобы познакомится")
    sleep(60)
    while True:
        msg = get_killed(night)
        bot.send_message(message.chat.id, msg)
        if not night:
            bot.send_message(message.chat.id, "Город засыпает, просыпается мафия, Наступила ночь")
        else:
            bot.send_message(message.chat.id, "Город просыпается. Наступил день")
        winner = db.check_winner()
        if winner == "Мафия" or winner == "Горожане":
            game = False
            bot.send_message(message.chat.id, f"Игра окончена победили: {winner}")
            return
        db.clear(dead=False)
        night = not night
        alive = db.get_all_alive()
        alive = "\n".join(alive)
        bot.send_message(message.chat.id, f"В игре: \n{alive}")
        sleep(60)
        autoplay_mafia() if night else autoplay_citizen(message)
        
@bot.message_handler(func=lambda message: message.text.lower() == 'готов играть' and message.chat.type == "private")
def send_text(message: Message):
    bot.send_message(message.chat.id, f"{message.from_user.first_name} играть")
    bot.send_message(message.chat.id, "Вы добавлены в игру")
    db.insert_player(message.from_user.id, message.from_user.first_name)
    
@bot.message_handler(commands=['start'])
def game_on(message: Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Готов играть"))
    bot.send_message(message.chat.id, "Если хотите играть, нажмите кнопку ниже", reply_markup=keyboard)
    
@bot.message_handler(commands=['play'])
def game_start(message: Message):
    global game
    players = db.player_amount()
    if players >= 5 and not game:
        db.set_roles(players)
        players_roles = db.get_players_roles()
        mafia_names = db.get_mafia_username()
        for player_id, role in players_roles:
            try:
                bot.send_message(player_id, role)
            except Exception:
                continue
            if role == 'mafia':
                bot.send_message(player_id, f"Все члены мафии: \n{mafia_names}")
        db.clear(dead=True)
        game = True
        bot.send_message(message.chat.id, "Игра началась!")
        game_llop(message)
        return
    bot.send_message(message.chat.id, "Недостаточно игроков!")
    for i in range(5 - players):
        bot_name = f"robot{i}"
        db.insert_player(i, bot_name)
        bot.send_message(message.chat.id, f"{bot_name} добавлен!")
        sleep(0.2)
    game_start(message)
        
@bot.message_handler(commands=["kick"])
def kick(message: Message):
    username = ''.join(message.text.split(" ")[1:])
    usernames = db.get_all_alive()
    if not night:
        if not username in usernames:
            bot.send_message(message.chat.id, "Такого имени нет")
            return
        voted = db.vote("citizen_vote", username, message.from_user.id)
        if voted:
            bot.send_message(message.chat.id, "Ваш голос учитан")
            return
        bot.send_message(message.chat.id, "У вас больше нет права голосовать")
        return
    bot.send_message(message.chat.id, "Сейчас ночь вы не можете никого выгнать")
    
@bot.message_handler(commands=['kill'])
def kill(message: Message):
    username = ' '.join(message.text.split(" ")[1:])
    usernames = db.get_mafia_username()
    if night and message.from_user.first_name in mafia_usernames:
        if not username in usernames:
            bot.send_message(message.chat.id, "Еакого имени нет")
            return
        voted = db.vote("mafia_vote", username, message.from_user.id)
        if voted:
            bot.send_message(message.chat.id, "Ваш голос учитан")
            return
        bot.send_message(message.chat.id, "У вас больше нет прав голосовать")
        return
    bot.send_message(message.chat.id, "Сейчас убивать нельзя")
        
bot.polling(non_stop=True, interval=1)
