import logging
import json
import os
import random
import asyncio
import httpx 

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler
)
from telegram.constants import ParseMode

# ----------------------------
# 1. कॉन्फ़िगरेशन एरिया (जरूरी सेटिंग्स)
# ----------------------------

# आपका Telegram बॉट टोकन
BOT_TOKEN = "7669431568:AAHkktsi8UnQb1IyorxHqsE4pgZlCmR6GYQ" # कृपया इसे बदलें
# आपका एडमिन यूजर आईडी (इसे अपडेट करना न भूलें)
ADMIN_ID = 7420417469 

# अनिवार्य चैनल का ID (जहाँ यूजर को जॉइन करना जरूरी है)
CHANNEL_ID = -1003122999249
CHANNEL_LINK = "https://t.me/kingofak_info" 

# API एंडपॉइंट्स और टोकन
NUM_OSINT_API = "https://spyshadow.site/num-osint.php?number={number}&Token=lundlelosaalo"
VEHICLE_OSINT_API = "https://rc-info-ng.vercel.app/?rc={rc_number}"
# ***AADHAAR_OSINT_API UPDATED HERE (Previous change retained):***
AADHAAR_OSINT_API = "https://spyshadow.site/adhaar.php?term={aadhaar}"
# नया API
TG_USER_INFO_API = "https://tg-info-neon.vercel.app/user-details?user={user_id}" 


# पॉइंट सिस्टम कॉन्फ़िगरेशन
SEARCH_COST = 1        
REFERRAL_BONUS = 2     
INITIAL_BONUS_POINTS = 5 

# यूजर डेटा स्टोरेज फाइल
USER_DATA_FILE = 'user_data.json'

# ConversationHandler स्टेट्स (नया स्टेट जोड़ा गया है)
(
    SELECTING_ACTION,
    GETTING_NUMBER,
    GETTING_VEHICLE,
    GETTING_AADHAAR,
    GETTING_TG_USER_ID, # नया स्टेट: TG User Info के लिए
    ADMIN_BROADCAST_MSG,
    ADMIN_ADD_BALANCE_ID,
    ADMIN_ADD_BALANCE_POINTS,
    ADMIN_REMOVE_BALANCE_ID,
    ADMIN_REMOVE_BALANCE_POINTS,
    SELECTING_LANGUAGE, 
) = range(11) # रेंज अपडेट की गई

# लॉगिंग सेट अप
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------------
# 2. मल्टी-लिंगुअल टेक्स्ट कॉन्फ़िगरेशन (HTML/इमोजी के साथ प्रोफेशनल लुक)
# ----------------------------

BOT_TEXTS = {
    # सामान्य / General
    'welcome_message': {
        'hi': "👋 <b>Namaste {name}!</b> <i>OSINT Bot</i> में आपका स्वागत है।",
        'en': "👋 <b>Hello {name}!</b> Welcome to the <i>OSINT Bot</i>.",
    },
    'points_info': {
        'hi': "💰 आपके पास अभी <b>{points}</b> points हैं। हर search पर <b>{cost}</b> point खर्च होगा।",
        'en': "💰 You currently have <b>{points}</b> points. Each search costs <b>{cost}</b> point.",
    },
    'menu_prompt': {
        'hi': "👇 <i>कृपया नीचे दिए गए buttons से अपना action चुनें:</i>",
        'en': "👇 <i>Please select your action from the buttons below:</i>",
    },
    'invalid_option': {
        'hi': "❌ आपने <b>गलत ऑप्शन</b> चुना है। कृपया menu से चुनें।",
        'en': "❌ You selected an <b>invalid option</b>. Please choose from the menu.",
    },
    'cancel_message': {
        'hi': "🚫 <b>Operation Cancelled.</b> आपके पास अभी <b>{points}</b> points हैं।\n\n👇 <i>कृपया नीचे दिए गए buttons से अपना action चुनें:</i>",
        'en': "🚫 <b>Operation Cancelled.</b> You currently have <b>{points}</b> points.\n\n👇 <i>Please select your action from the buttons below:</i>",
    },
    'points_low': {
        'hi': "🛑 <b>Points Kam Hain!</b> आपके पास अभी सिर्फ <b>{points}</b> points हैं। इस search के लिए <b>{cost}</b> point की ज़रूरत है।\n\n🎁 <i>Points कमाने के लिए</i> <b>Refer and Earn</b> <i>का उपयोग करें।</i>",
        'en': "🛑 <b>Low Points!</b> You only have <b>{points}</b> points. This search requires <b>{cost}</b> point.\n\n🎁 <i>Please use</i> <b>Refer and Earn</b> <i>to gain more points.</i>",
    },
    'success_deduction': {
        'hi': "✅ <b>Data Received!</b> Info निकाल रहा है... <i>(आपके <b>{cost}</b> point cut गए हैं। बाकी points: <b>{new_points}</b>)</i>",
        'en': "✅ <b>Data Received!</b> Retrieving information... <i>(Your <b>{cost}</b> point has been deducted. Remaining points: <b>{new_points}</b>)</i>",
    },
    'no_info_found': {
        'hi': "😔 <b>Maaf Kijiyega!</b> इसके लिए कोई info नहीं मिली। Points वापस कर दिए गए हैं।",
        'en': "😔 <b>Sorry!</b> No information found for this query. Points have been refunded.",
    },
    'api_error': {
        'hi': "⚠️ <b>API Error!</b> Data fetch करने में गड़बड़ हुई। <i>कृपया फिर कोशिश करें।</i> <code>Error: {error}</code>",
        'en': "⚠️ <b>API Error!</b> An error occurred while fetching data. <i>Please try again.</i> <code>Error: {error}</code>",
    },
    
    # सब्सक्रिप्शन / Subscription
    'sub_prompt': {
        'hi': "🚨 <b>Bot Shuru Karne Ke Liye Yeh Channel Join Karna Zaroori Hai!</b> 🚨\n\n👉 <i>कृपया channel join करें और फिर</i> <b>'Verify Karein'</b> <i>button दबाएँ।</i>",
        'en': "🚨 <b>Channel Subscription is Mandatory to Start the Bot!</b> 🚨\n\n👉 <i>Please join the channel and then press the</i> <b>'Verify'</b> <i>button.</i>",
    },
    'btn_join': {'hi': "🔗 Channel Join Karein", 'en': "🔗 Join Channel"},
    'btn_verify': {'hi': "✅ Verify Karein", 'en': "✅ Verify"},
    'sub_failed': {
        'hi': "❌ <b>Abhi Bhi Join Nahi Kiya!</b> <i> कृपया पहले channel join करें और फिर दोबारा verify करें।</i>",
        'en': "❌ <b>Not Joined Yet!</b> <i>Please join the channel first and then try verifying again.</i>",
    },
    'bonus_given': {
        'hi': "🎉 <b>Dhanyawad!</b> आपने channel join कर लिया है।\n🎁 आपको <b>{bonus}</b> free points मिले हैं। <b>Total points:</b> <code>{new_points}</code>.",
        'en': "🎉 <b>Thank You!</b> You have joined the channel.\n🎁 You have received <b>{bonus}</b> free points. <b>Total points:</b> <code>{new_points}</code>.",
    },
    'sub_success': {
        'hi': "✅ <b>Dhanyawad!</b> आपने channel join कर लिया है।",
        'en': "✅ <b>Thank You!</b> You have joined the channel.",
    },
    
    # भाषा चयन / Language Selection
    'lang_prompt': {
        'hi': "🌎 <b>Bhasha Chunein:</b> <i>कृपया अपनी पसंद की भाषा (language) चुनें:</i>",
        'en': "🌎 <b>Select Language:</b> <i>Please select your preferred language:</i>",
    },

    # सर्च मेनू / Search Menus
    'prompt_number': {
        'hi': "🔍 <b>Mobile Number Search:</b> <i>कृपया वह</i> <b>mobile number</b> <i>भेजें जिसका info चाहिए:</i>",
        'en': "🔍 <b>Mobile Number Search:</b> <i>Please send the</i> <b>mobile number</b> <i>for which you want information:</i>",
    },
    'prompt_vehicle': {
        'hi': "🚗 <b>Vehicle Info Search:</b> <i>कृपया</i> <b>Vehicle (RC) Number</b> <i>(e.g.,</i> <code>DL12F2574</code>) <i>भेजें:</i>",
        'en': "🚗 <b>Vehicle Info Search:</b> <i>Please send the</i> <b>Vehicle (RC) Number</b> <i>(e.g.,</i> <code>DL12F2574</code>)<i>:</i>",
    },
    'prompt_aadhaar': {
        'hi': "🪪 <b>Aadhaar Info Search:</b> <i>कृपया</i> <b>Aadhaar Number</b> <i>(12 digit) भेजें:</i>",
        'en': "🪪 <b>Aadhaar Info Search:</b> <i>Please send the</i> <b>Aadhaar Number</b> <i>(12 digit):</i>",
    },
    'prompt_tg_user_id': {
        'hi': "👤 <b>Telegram User Info:</b> <i>कृपया वह</i> <b>Telegram User ID</b> <i>भेजें (सिर्फ नंबर):</i>",
        'en': "👤 <b>Telegram User Info:</b> <i>Please send the</i> <b>Telegram User ID</b> <i>(numbers only):</i>",
    },
    'invalid_number': {
        'hi': "❌ <b>Invalid Input!</b> <i> कृपया valid Mobile Number ही भेजें।</i> दोबारा कोशिश करें या /cancel करें।",
        'en': "❌ <b>Invalid Input!</b> <i>Please send a valid Mobile Number.</i> Try again or /cancel.",
    },
    'invalid_vehicle': {
        'hi': "❌ <b>Invalid Input!</b> <i> कृपया valid Vehicle (RC) Number ही भेजें।</i> दोबारा कोशिश करें या /cancel करें।",
        'en': "❌ <b>Invalid Input!</b> <i>Please send a valid Vehicle (RC) Number.</i> Try again or /cancel.",
    },
    'invalid_aadhaar': {
        'hi': "❌ <b>Invalid Input!</b> <i> कृपया valid Aadhaar Number (12 digit) ही भेजें।</i> दोबारा कोशिश करें या /cancel करें।",
        'en': "❌ <b>Invalid Input!</b> <i>Please send a valid Aadhaar Number (12 digit) ही भेजें।</i> Try again or /cancel.",
    },
    'invalid_tg_user_id': {
        'hi': "❌ <b>Invalid Input!</b> <i> कृपया valid Telegram User ID (सिर्फ नंबर) ही भेजें।</i> दोबारा कोशिश करें या /cancel करें।",
        'en': "❌ <b>Invalid Input!</b> <i>Please send a valid Telegram User ID (numbers only).</i> Try again or /cancel.",
    },
    
    # नया TG User Info आउटपुट
    'tg_info_output': {
        'hi': (
            "👤 <b>Telegram User Details</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• <b>ID:</b> <code>{id}</code>\n"
            "• <b>First Name:</b> <code>{first_name}</code>\n"
            "• <b>Last Name:</b> <code>{last_name}</code>\n"
            "• <b>Is Bot:</b> <code>{is_bot}</code>\n"
            "• <b>Is Active:</b> <code>{is_active}</code>\n"
            "• <b>Total Groups:</b> <code>{total_groups}</code>\n"
            "• <b>Total Msg Count:</b> <code>{total_msg_count}</code>\n"
            "• <b>First Msg Date:</b> <code>{first_msg_date}</code>\n"
        ),
        'en': (
            "👤 <b>Telegram User Details</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• <b>ID:</b> <code>{id}</code>\n"
            "• <b>First Name:</b> <code>{first_name}</code>\n"
            "• <b>Last Name:</b> <code>{last_name}</code>\n"
            "• <b>Is Bot:</b> <code>{is_bot}</code>\n"
            "• <b>Is Active:</b> <code>{is_active}</code>\n"
            "• <b>Total Groups:</b> <code>{total_groups}</code>\n"
            "• <b>Total Msg Count:</b> <code>{total_msg_count}</code>\n"
            "• <b>First Msg Date:</b> <code>{first_msg_date}</code>\n"
        ),
    },

    # रेफरल / Referral
    'referral_message': {
        'hi': "🎉 <b>Badhai Ho!</b> आपके referral link से नए user (<code>{name}</code>) ने bot शुरू किया है।\n💰 आपको <b>{bonus}</b> points मिले हैं। <b>Total points:</b> <code>{new_points}</code>",
        'en': "🎉 <b>Congratulations!</b> A new user (<code>{name}</code>) started the bot using your referral link.\n💰 You have received <b>{bonus}</b> points. <b>Total points:</b> <code>{new_points}</code>",
    },
    'referral_started': {
        'hi': "🤝 आपने <code>{referrer_id}</code> के द्वारा invite किया है। <i>Points कमाने के लिए अब आप search शुरू कर सकते हैं!</i>",
        'en': "🤝 You were invited by <code>{referrer_id}</code>. <i>You can now start searching to earn points!</i>",
    },
    'refer_earn_title': {
        'hi': "🔗 <b>Refer Aur Kamao!</b> 🤑",
        'en': "🔗 <b>Refer and Earn!</b> 🤑",
    },
    'refer_earn_details': {
        'hi': "हर safal referral पर आपको <b>{bonus}</b> points मिलेंगे। <i>(हर search पर <b>{cost}</b> point खर्च होगा)</i>",
        'en': "You will get <b>{bonus}</b> points for every successful referral. <i>(Each search costs <b>{cost}</b> point)</i>",
    },
    'refer_link_prompt': {
        'hi': "✨ <b>Aapka Referral Link (Ise Share Karein):</b>\n\n<code>{link}</code>\n\n👉 <i>Link copy करें और अपने दोस्तों के साथ share करें!</i>",
        'en': "✨ <b>Your Referral Link (Share This):</b>\n\n<code>{link}</code>\n\n👉 <i>Copy the link and share it with your friends!</i>",
    },

    # एडमिन / Admin
    'admin_panel_title': {'hi': "👑 <b>Admin Panel</b> ⚙️", 'en': "👑 <b>Admin Panel</b> ⚙️"},
    'admin_prompt': {'hi': "👇 <i>कृपया नीचे दिए गए buttons से अपना action चुनें:</i>", 'en': "👇 <i>Please select your action from the buttons below:</i>"},
    'admin_denied': {'hi': "❌ <b>Access Denied!</b> <i>आप admin नहीं हैं। यह command आपके लिए नहीं है।</i>", 'en': "❌ <b>Access Denied!</b> <i>You are not an admin. This command is not for you.</i>"},
    'admin_broadcast_start': {'hi': "📢 <b>Broadcast Shuru:</b> <i>वह message भेजें जो सभी users को भेजना है।</i> (/admincancel से रद्द करें)", 'en': "📢 <b>Start Broadcast:</b> <i>Send the message you want to broadcast to all users.</i> (/admincancel to cancel)"},
    'admin_add_id_prompt': {'hi': "➕ <b>Points Jodein:</b> <i>किसको Points देने हैं? User</i> <b>ID</b> <i>भेजें:</i> (/admincancel से रद्द करें)", 'en': "➕ <b>Add Points:</b> <i>To whom should points be added? Send User</i> <b>ID</b><i>:</i> (/admincancel to cancel)"},
    'admin_add_points_prompt': {'hi': "💰 <b>Points Jodein:</b> <i>कितने points जोड़ने हैं? Sankhya (number) भेजें:</i>", 'en': "💰 <b>Add Points:</b> <i>How many points to add? Send the number:</i>"},
    'admin_remove_id_prompt': {'hi': "➖ <b>Points Ghataein:</b> <i>किसके Points निकालने हैं? User</i> <b>ID</b> <i>भेजें:</i> (/admincancel से रद्द करें)", 'en': "➖ <b>Remove Points:</b> <i>Whose points should be removed? Send User</i> <b>ID</b><i>:</i> (/admincancel to cancel)"},
    'admin_remove_points_prompt': {'hi': "💰 <b>Points Ghataein:</b> <i>कितने points निकालने हैं? Sankhya (number) भेजें:</i>", 'en': "💰 <b>Remove Points:</b> <i>How many points to remove? Send the number:</i>"},
    'admin_invalid_id': {'hi': "❌ <b>Invalid ID!</b> <i> कृपया valid User ID (number) ही भेजें।</i> दोबारा कोशिश करें।", 'en': "❌ <b>Invalid ID!</b> <i>Please send a valid User ID (number).</i> Try again."},
    'admin_invalid_points': {'hi': "❌ <b>Invalid Points!</b> <i> कृपया points की valid sankhya (number) ही भेजें।</i> दोबारा कोशिश करें।", 'en': "❌ <b>Invalid Points!</b> <i>Please send a valid number of points.</i> Try again."},
    'admin_add_success': {'hi': "✅ <b>Success!</b> <b>{points}</b> points User ID <code>{id}</code> को जोड़े गए।\n<b>New Points:</b> <code>{new_points}</code>", 'en': "✅ <b>Success!</b> Successfully added <b>{points}</b> points to User ID <code>{id}</code>.\n<b>New Points:</b> <code>{new_points}</code>"},
    'admin_remove_success': {'hi': "✅ <b>Success!</b> <b>{points}</b> points User ID <code>{id}</code> से हटाए गए।\n<b>New Points:</b> <code>{new_points}</code>", 'en': "✅ <b>Success!</b> Successfully removed <b>{points}</b> points from User ID <code>{id}</code>.\n<b>New Points:</b> <code>{new_points}</code>"},
    'admin_notify_add': {'hi': "➕ <b>Admin Ne Points Jode!</b> आपके account में <b>{points}</b> points जोड़े गए हैं।\n<b>New Points:</b> <code>{new_points}</code>", 'en': "➕ <b>Admin Added Points!</b> <b>{points}</b> points have been added to your account.\n<b>New Points:</b> <code>{new_points}</code>"},
    'admin_notify_remove': {'hi': "➖ <b>Admin Ne Points Hataye!</b> आपके account से <b>{points}</b> points हटाए गए हैं।\n<b>New Points:</b> <code>{new_points}</code>", 'en': "➖ <b>Admin Removed Points!</b> <b>{points}</b> points have been removed from your account.\n<b>New Points:</b> <code>{new_points}</code>"},
}


def get_text(user_id: int, key: str, **kwargs) -> str:
    """यूजर की चुनी हुई भाषा के आधार पर टेक्स्ट लौटाता है।"""
    data = load_user_data()
    lang = data.get(str(user_id), {}).get('lang', 'hi') # Default to Hindi/Hinglish
    
    text_template = BOT_TEXTS.get(key, {}).get(lang, f"!!Missing Text for {key} in {lang}!!")
    return text_template.format(**kwargs)


# ----------------------------
# 3. स्टोरेज और सहायक फंक्शन (BONUS FLAG ADDED)
# ----------------------------

def load_user_data():
    """JSON फाइल से यूजर डेटा लोड करता है।"""
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            logger.error("Error reading or parsing user data file. Starting fresh.")
            return {}
    return {}

def save_user_data(data):
    """यूजर डेटा को JSON फाइल में सेव करता है।"""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def initialize_user(user_id):
    """अगर यूजर नया है तो उसे पॉइंट्स, रेफरल और लैंग्वेज फ्लैग के साथ इनिशियलाइज़ करता है।"""
    data = load_user_data()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {
            'points': 1000, 
            'referred_by': None, 
            'searches_done': 0, 
            'bonus_given': False,
            'lang': None # भाषा अभी तक नहीं चुनी गई है
        }
        save_user_data(data)
    
    # सुनिश्चित करें कि 'lang' और 'bonus_given' key मौजूद है
    if 'lang' not in data[user_id_str]:
        data[user_id_str]['lang'] = None
    if 'bonus_given' not in data[user_id_str]:
        data[user_id_str]['bonus_given'] = False
        
    save_user_data(data)
        
    return data[user_id_str]

def get_user_points(user_id):
    """यूजर के मौजूदा पॉइंट्स दिखाता है।"""
    data = load_user_data()
    return data.get(str(user_id), {}).get('points', 0)

def update_user_points(user_id, points_change):
    """यूजर के पॉइंट्स में बदलाव करता है।"""
    data = load_user_data()
    user_id_str = str(user_id)
    user_data = initialize_user(user_id) # Ensure user is initialized

    current_points = user_data['points']
    new_points = current_points + points_change
    data[user_id_str]['points'] = max(0, new_points) # पॉइंट्स 0 से नीचे नहीं जाएंगे

    # Searches done को ट्रैक करें
    if points_change < 0:
        data[user_id_str]['searches_done'] = data[user_id_str].get('searches_done', 0) + 1

    save_user_data(data)
    return data[user_id_str]['points']

def chunk_data(data_list, chunk_size):
    """डेटा लिस्ट को छोटे चंक्स में बाँटता है।"""
    for i in range(0, len(data_list), chunk_size):
        yield data_list[i:i + chunk_size]

# ----------------------------
# 4. भाषा चयन हैंडलर्स (समाधान 1 यहाँ है)
# ----------------------------

async def prompt_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """यूजर को भाषा चुनने के लिए प्रॉम्प्ट करता है।"""
    user_id = update.effective_user.id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇳 Hinglish", callback_data='lang_hi')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')]
    ])
    
    # Message source (handle inline or text message)
    msg_source = update.callback_query.message if update.callback_query else update.message

    await msg_source.reply_text(
        get_text(user_id, 'lang_prompt'),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    return SELECTING_LANGUAGE


async def select_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """यूजर की भाषा चयन को हैंडल करता है और सेव करता है।"""
    query = update.callback_query
    user_id = query.from_user.id
    lang_code = query.data.split('_')[1] # 'lang_hi' or 'lang_en'
    
    await query.answer()

    # भाषा सेव करें
    data = load_user_data()
    data[str(user_id)]['lang'] = lang_code
    save_user_data(data)

    if lang_code == 'hi':
        confirmation_text = "✅ <b>Bhasha Safalta Poorvak Hinglish chuni gayi hai.</b> Bot shuru ho raha hai..."
    else:
        confirmation_text = "✅ <b>Language successfully set to English.</b> Starting the bot now..."

    await query.edit_message_text(
        text=confirmation_text,
        parse_mode=ParseMode.HTML
    )
    
    # /start कमांड को chat में दोबारा ट्रिगर करें ताकि ConversationHandler सही स्टेट में वापस आ जाए
    
    # 1. एक नया मैसेज ऑब्जेक्ट बनाएं जिसमें /start कमांड हो
    temp_message = Update(
        update_id=random.randint(1, 10000), 
        message=query.message.copy(
            text="/start", 
            message_id=query.message.message_id + 1, 
            from_user=query.from_user, 
            chat=query.message.chat
        )
    )
    
    # 2. bot flow को फिर से शुरू करने के लिए /start कमांड प्रोसेस करें
    await context.application.process_update(temp_message)
    
    return ConversationHandler.END # कन्वर्सेशन को खत्म करें, /start नया शुरू करेगा

# ----------------------------
# 5. चैनल सदस्यता जांच और मेन मेनू
# ----------------------------

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """जाँच करता है कि यूजर ने चैनल जॉइन किया है या नहीं।"""
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking subscription for {user_id}: {e}")
        return True 


def get_main_keyboard():
    """मेन मेनू के लिए ReplyKeyboardMarkup बनाता है। (नया TG बटन जोड़ा गया)"""
    return ReplyKeyboardMarkup(
        [
            ["🔍 Number to Info", "🚗 Vehicle Info"],
            ["🪪 Aadhaar Info", "👤 Telegram User Info"], # नया बटन
            ["🤑 Refer and Earn", "🌎 Change Language"] # नया बटन
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """यूजर को मेन मेनू दिखाता है।"""
    user = update.effective_user
    points = get_user_points(user.id)
    
    # Text retrieval (भाषा के अनुसार)
    welcome_msg = get_text(user.id, 'welcome_message', name=user.first_name)
    points_info = get_text(user.id, 'points_info', points=points, cost=SEARCH_COST)
    menu_prompt = get_text(user.id, 'menu_prompt')
    
    # **कीबोर्ड वापस भेजने के लिए**
    await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"{welcome_msg}\n\n"
            f"{points_info}\n\n"
            f"{menu_prompt}"
        ),
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return SELECTING_ACTION


async def show_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """सब्सक्रिप्शन के लिए मैसेज और Inline Keyboard भेजता है।"""
    user_id = update.effective_user.id
    
    # यहाँ भाषा 'hi' को default मानकर चलते हैं क्योंकि यूजर ने अभी भाषा नहीं चुनी है
    join_btn = get_text(user_id, 'btn_join')
    verify_btn = get_text(user_id, 'btn_verify')

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(join_btn, url=CHANNEL_LINK)],
        [InlineKeyboardButton(verify_btn, callback_data='check_sub')]
    ])
    
    msg_source = update.callback_query.message if update.callback_query else update.message
    
    await msg_source.reply_text(
        get_text(user_id, 'sub_prompt'),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """'/start' कमांड को हैंडल करता है।"""
    user = update.effective_user
    user_id_str = str(user.id)
    user_data = initialize_user(user.id) # 1. यूजर को इनिशियलाइज़ करना

    # 1. रेफरल हैंडलिंग
    if context.args and not user_data.get('referred_by'):
        referrer_id_str = context.args[0].replace('ref_', '')
        if referrer_id_str.isdigit() and referrer_id_str != user_id_str:
            data = load_user_data()
            if referrer_id_str in data:
                if not data[user_id_str].get('referred_by'):
                    data[user_id_str]['referred_by'] = referrer_id_str
                    
                    # रेफरर को बोनस देना
                    update_user_points(int(referrer_id_str), REFERRAL_BONUS)
                    referrer_points = get_user_points(int(referrer_id_str))
                    
                    # रेफरर को नोटिफाई करें (referrer की भाषा में)
                    await context.bot.send_message(
                        chat_id=int(referrer_id_str),
                        text=get_text(int(referrer_id_str), 'referral_message', 
                                      name=user.first_name, bonus=REFERRAL_BONUS, new_points=referrer_points),
                        parse_mode=ParseMode.HTML
                    )
                    save_user_data(data)
                    # रेफरल द्वारा आए नए यूजर को नोटिफाई करें (अभी 'hi' default)
                    await update.message.reply_text(
                        get_text(user.id, 'referral_started', referrer_id=referrer_id_str),
                        parse_mode=ParseMode.HTML
                    )

    # 2. चैनल सदस्यता जांच
    if not await check_subscription(user.id, context):
        await show_subscription_message(update, context)
        return ConversationHandler.END 

    # 3. भाषा चयन प्रॉम्प्ट
    if not user_data.get('lang'):
        return await prompt_language_selection(update, context)

    # 4. मेन मेनू दिखाना
    return await show_main_menu(update, context)


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Verify Karein बटन पर क्लिक करने पर सब्सक्रिप्शन चेक करता है और बोनस देता है।"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    user_data = initialize_user(user_id) # Ensure user data is initialized

    if await check_subscription(user_id, context):
        user_id_str = str(user_id)
        bonus_given = user_data.get('bonus_given', False)

        if not bonus_given:
            # 1. बोनस पॉइंट्स add करें
            new_points = update_user_points(user_id, INITIAL_BONUS_POINTS)
            
            # 2. Flag set करें
            data = load_user_data()
            data[user_id_str]['bonus_given'] = True
            save_user_data(data)

            await query.edit_message_text(
                get_text(user_id, 'bonus_given', bonus=INITIAL_BONUS_POINTS, new_points=new_points),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                get_text(user_id, 'sub_success'),
                parse_mode=ParseMode.HTML
            )
        
        # 3. भाषा चयन प्रॉम्प्ट
        user_data = load_user_data().get(user_id_str, {})
        if not user_data.get('lang'):
            # Edit the message to show the language prompt
            return await prompt_language_selection(update, context)
        
        # अगर भाषा पहले से चुनी हुई है तो मेन मेनू दिखाएँ
        temp_message = Update(
            update_id=random.randint(1, 10000), 
            message=query.message.copy(
                text="/start", 
                message_id=query.message.message_id + 1, 
                from_user=query.from_user, 
                chat=query.message.chat
            )
        )
        await context.application.process_update(temp_message)
        
        return ConversationHandler.END

    else:
        # अगर जॉइन नहीं किया
        join_btn = get_text(user_id, 'btn_join')
        verify_btn = get_text(user_id, 'btn_verify')
        
        await query.edit_message_text(
            get_text(user_id, 'sub_failed'),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(join_btn, url=CHANNEL_LINK)],
                [InlineKeyboardButton(verify_btn, callback_data='check_sub')]
            ]),
            parse_mode=ParseMode.HTML
        )
    return ConversationHandler.END


# ----------------------------
# 6. मेन्यू बटन हैंडलर्स
# ----------------------------

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """मेनू बटन क्लिक्स को हैंडल करता है और सही स्टेट में ले जाता है।"""
    user = update.effective_user
    text = update.message.text
    
    if not await check_subscription(user.id, context):
        await show_subscription_message(update, context)
        return ConversationHandler.END

    points = get_user_points(user.id)
    
    # सर्च के लिए पॉइंट्स चेक (Icons हटा दिए गए)
    if text in ["🔍 Number to Info", "🚗 Vehicle Info", "🪪 Aadhaar Info", "👤 Telegram User Info"]: # नया बटन जोड़ा गया
        if points < SEARCH_COST:
            await update.message.reply_text(
                get_text(user.id, 'points_low', points=points, cost=SEARCH_COST),
                reply_markup=get_main_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return SELECTING_ACTION 
    
    if "Number to Info" in text:
        await update.message.reply_text(get_text(user.id, 'prompt_number'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return GETTING_NUMBER
    
    elif "Vehicle Info" in text:
        await update.message.reply_text(get_text(user.id, 'prompt_vehicle'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return GETTING_VEHICLE
    
    elif "Aadhaar Info" in text:
        await update.message.reply_text(get_text(user.id, 'prompt_aadhaar'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return GETTING_AADHAAR
    
    elif "Telegram User Info" in text: # नया TG User Info हैंडलर
        await update.message.reply_text(get_text(user.id, 'prompt_tg_user_id'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return GETTING_TG_USER_ID
    
    elif "Refer and Earn" in text:
        return await refer_and_earn(update, context)
        
    elif "Change Language" in text: # नया Language Change बटन
        # Language selection message sent via inline, we stay in SELECTING_ACTION state
        await prompt_language_selection(update, context)
        return SELECTING_ACTION


    # अगर कोई और मैसेज आता है
    await update.message.reply_text(get_text(user.id, 'invalid_option'), reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
    return SELECTING_ACTION


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """किसी भी स्टेट से कन्वर्सेशन को कैंसिल करता है और मेनू दिखाता है।"""
    user = update.effective_user
    
    if not await check_subscription(user.id, context):
        await show_subscription_message(update, context)
        return ConversationHandler.END

    points = get_user_points(user.id)
    await update.message.reply_text(
        get_text(user.id, 'cancel_message', points=points),
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return SELECTING_ACTION


# ----------------------------
# 7. OSINT सर्च हैंडलर्स (कीबोर्ड फिक्स यहाँ है)
# ----------------------------

async def handle_number_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """मोबाइल नंबर से OSINT डेटा निकालता है और पॉइंट्स काटता है।"""
    user = update.effective_user
    number = update.message.text.strip()
    
    if not number.isdigit() or len(number) < 10 or len(number) > 12:
        await update.message.reply_text(get_text(user.id, 'invalid_number'), parse_mode=ParseMode.HTML)
        return GETTING_NUMBER

    # पॉइंट डिडक्शन
    new_points = update_user_points(user.id, -SEARCH_COST)
    await update.message.reply_text(
        get_text(user.id, 'success_deduction', cost=SEARCH_COST, new_points=new_points),
        parse_mode=ParseMode.HTML
    )
    
    api_url = NUM_OSINT_API.format(number=number)
    lang = load_user_data().get(str(user.id), {}).get('lang', 'hi')
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url)
            data = response.json()

        if not data or not isinstance(data, list):
            await update.message.reply_text(get_text(user.id, 'no_info_found'), parse_mode=ParseMode.HTML)
            update_user_points(user.id, SEARCH_COST) # पॉइंट्स वापस करें
            return await cancel_command(update, context)

        # Chunking: 1 message mein 2 records
        chunk_size = 2
        
        for i, chunk in enumerate(chunk_data(data, chunk_size)):
            if lang == 'hi':
                message_text = f"📱 <b>Mobile Number Info</b> <i>(Result {i*chunk_size + 1} se {min((i+1)*chunk_size, len(data))})</i>\n\n"
            else:
                message_text = f"📱 <b>Mobile Number Info</b> <i>(Result {i*chunk_size + 1} to {min((i+1)*chunk_size, len(data))})</i>\n\n"

            for j, record in enumerate(chunk):
                if lang == 'hi':
                    record_text = (
                        f"<b>--- Record {j+1} ---</b>\n"
                        f"• <b>Naam:</b> <code>{record.get('name', 'N/A')}</code>\n"
                        f"• <b>Pita ka Naam:</b> <code>{record.get('father_name', 'N/A')}</code>\n"
                        f"• <b>Pura Pata:</b> <code>{record.get('address', 'N/A')}</code>\n"
                        f"• <b>Alternate Mobile:</b> <code>{record.get('alternate_mobile', 'N/A')}</code>\n"
                        f"• <b>Circle:</b> <code>{record.get('circle', 'N/A')}</code>\n"
                        f"• <b>ID Number:</b> <code>{record.get('id_number', 'N/A')}</code>\n"
                        f"• <b>Email:</b> <code>{record.get('email', 'N/A')}</code>\n"
                    )
                else:
                    record_text = (
                        f"<b>--- Record {j+1} ---</b>\n"
                        f"• <b>Name:</b> <code>{record.get('name', 'N/A')}</code>\n"
                        f"• <b>Father's Name:</b> <code>{record.get('father_name', 'N/A')}</code>\n"
                        f"• <b>Full Address:</b> <code>{record.get('address', 'N/A')}</code>\n"
                        f"• <b>Alternate Mobile:</b> <code>{record.get('alternate_mobile', 'N/A')}</code>\n"
                        f"• <b>Circle:</b> <code>{record.get('circle', 'N/A')}</code>\n"
                        f"• <b>ID Number:</b> <code>{record.get('id_number', 'N/A')}</code>\n"
                        f"• <b>Email:</b> <code>{record.get('email', 'N/A')}</code>\n"
                    )

                message_text += record_text + "\n"
            await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
        
        # ***[सुधार: मेनू दिखाएँ]***
        return await show_main_menu(update, context)

    except (httpx.RequestError, json.JSONDecodeError) as e:
        await update.message.reply_text(get_text(user.id, 'api_error', error=str(e)), parse_mode=ParseMode.HTML)
        update_user_points(user.id, SEARCH_COST) 
        logger.error(f"Number OSINT API Error: {e}")
        return await cancel_command(update, context) # असफल होने पर cancel करें
    
async def handle_vehicle_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """व्हीकल नंबर से OSINT डेटा निकालता है और पॉइंट्स काटता है।"""
    user = update.effective_user
    rc_number = update.message.text.strip().upper()
    
    if not rc_number or len(rc_number) < 7:
        await update.message.reply_text(get_text(user.id, 'invalid_vehicle'), parse_mode=ParseMode.HTML)
        return GETTING_VEHICLE

    new_points = update_user_points(user.id, -SEARCH_COST)
    await update.message.reply_text(
        get_text(user.id, 'success_deduction', cost=SEARCH_COST, new_points=new_points),
        parse_mode=ParseMode.HTML
    )

    api_url = VEHICLE_OSINT_API.format(rc_number=rc_number)
    lang = load_user_data().get(str(user.id), {}).get('lang', 'hi')

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url)
            data = response.json()

        if not data or data.get('rc_number') != rc_number: 
            await update.message.reply_text(get_text(user.id, 'no_info_found'), parse_mode=ParseMode.HTML)
            update_user_points(user.id, SEARCH_COST) 
            return await cancel_command(update, context)

        if 'owner' in data: del data['owner']

        if lang == 'hi':
            message_text = (
                "🚗 <b>Vehicle (RC) Info</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"• <b>RC Number:</b> <code>{data.get('rc_number', 'N/A')}</code>\n"
                f"• <b>Owner Ka Naam:</b> <code>{data.get('owner_name', 'N/A')}</code>\n"
                f"• <b>Pita Ka Naam:</b> <code>{data.get('father_name', 'N/A')}</code>\n"
                f"• <b>Model Name:</b> <code>{data.get('model_name', 'N/A')}</code>\n"
                f"• <b>Maker Model:</b> <code>{data.get('maker_model', 'N/A')}</code>\n"
                f"• <b>Fuel Type:</b> <code>{data.get('fuel_type', 'N/A')}</code>\n"
                f"• <b>Registration Date:</b> <code>{data.get('registration_date', 'N/A')}</code>\n"
                f"• <b>RTO:</b> <code>{data.get('rto', 'N/A')}</code>\n"
                f"• <b>Pata:</b> <code>{data.get('address', 'N/A')}</code>\n"
                f"• <b>City:</b> <code>{data.get('city', 'N/A')}</code>\n"
            )
        else:
            message_text = (
                "🚗 <b>Vehicle (RC) Information</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"• <b>RC Number:</b> <code>{data.get('rc_number', 'N/A')}</code>\n"
                f"• <b>Owner Name:</b> <code>{data.get('owner_name', 'N/A')}</code>\n"
                f"• <b>Father's Name:</b> <code>{data.get('father_name', 'N/A')}</code>\n"
                f"• <b>Model Name:</b> <code>{data.get('model_name', 'N/A')}</code>\n"
                f"• <b>Maker Model:</b> <code>{data.get('maker_model', 'N/A')}</code>\n"
                f"• <b>Fuel Type:</b> <code>{data.get('fuel_type', 'N/A')}</code>\n"
                f"• <b>Registration Date:</b> <code>{data.get('registration_date', 'N/A')}</code>\n"
                f"• <b>RTO:</b> <code>{data.get('rto', 'N/A')}</code>\n"
                f"• <b>Address:</b> <code>{data.get('address', 'N/A')}</code>\n"
                f"• <b>City:</b> <code>{data.get('city', 'N/A')}</code>\n"
            )
        
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
        # ***[सुधार: मेनू दिखाएँ]***
        return await show_main_menu(update, context)

    except (httpx.RequestError, json.JSONDecodeError) as e:
        await update.message.reply_text(get_text(user.id, 'api_error', error=str(e)), parse_mode=ParseMode.HTML)
        update_user_points(user.id, SEARCH_COST) 
        logger.error(f"Vehicle OSINT API Error: {e}")
        return await cancel_command(update, context) # असफल होने पर cancel करें
    

async def handle_aadhaar_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """आधार नंबर से OSINT डेटा निकालता है और पॉइंट्स काटता है।"""
    user = update.effective_user
    aadhaar = update.message.text.strip()
    
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        await update.message.reply_text(get_text(user.id, 'invalid_aadhaar'), parse_mode=ParseMode.HTML)
        return GETTING_AADHAAR

    new_points = update_user_points(user.id, -SEARCH_COST)
    await update.message.reply_text(
        get_text(user.id, 'success_deduction', cost=SEARCH_COST, new_points=new_points),
        parse_mode=ParseMode.HTML
    )

    api_url = AADHAAR_OSINT_API.format(aadhaar=aadhaar)
    lang = load_user_data().get(str(user.id), {}).get('lang', 'hi')
    
    try:
        # START: ADDING HEADERS AND ROBUST JSON PARSING
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json' 
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            
            response_text = response.text.strip()
            records = None # Initialize records
            text_to_parse = ""

            # 1. Pass 1: Attempt robust standard JSON parsing (with trimming)
            try:
                # Find the actual start of the JSON list/object to bypass leading non-JSON text
                start_index_list = response_text.find('[')
                start_index_obj = response_text.find('{')
                
                # Determine which start is first (if any)
                if start_index_list != -1 and (start_index_obj == -1 or start_index_list < start_index_obj):
                    text_to_parse = response_text[start_index_list:]
                elif start_index_obj != -1:
                    text_to_parse = response_text[start_index_obj:]
                else:
                    # If no valid JSON start is found, raise an error
                    raise json.JSONDecodeError("API returned invalid response text: No JSON start found", response_text, 0)
                
                # Now, attempt to parse the trimmed JSON text
                records = json.loads(text_to_parse)

            except json.JSONDecodeError as e:
                logger.warning(f"Aadhaar API returned non-standard JSON. Trying fallback fix. Error: {e}")
                
                # 2. Pass 2: Attempt fix for malformed quotes (Common fix for "Expecting property name enclosed in double quotes")
                try:
                    # Simple (risky) replacement: replace all single quotes with double quotes. 
                    # This fixes non-standard JSON like [ {'key': 'value'} ]
                    corrected_text = text_to_parse.replace("'", '"')
                    records = json.loads(corrected_text)
                    logger.info("Fallback fix successful (Replaced single quotes).")
                except Exception as inner_e:
                    # If the fix attempt also fails, raise the original error to be caught by the outer block
                    logger.error(f"Fallback parsing failed. Original JSONDecodeError: {e}")
                    raise e # Re-raise the original JSONDecodeError
            
        # The API response format seems to be a list directly
        if not records or not isinstance(records, list):
            await update.message.reply_text(get_text(user.id, 'no_info_found'), parse_mode=ParseMode.HTML)
            update_user_points(user.id, SEARCH_COST) 
            return await cancel_command(update, context)

        chunk_size = 2
        
        for i, chunk in enumerate(chunk_data(records, chunk_size)):
            if lang == 'hi':
                message_text = f"🪪 <b>Aadhaar Number Info</b> <i>(Result {i*chunk_size + 1} se {min((i+1)*chunk_size, len(records))})</i>\n\n"
            else:
                message_text = f"🪪 <b>Aadhaar Number Info</b> <i>(Result {i*chunk_size + 1} to {min((i+1)*chunk_size, len(records))})</i>\n\n"
            
            for j, record in enumerate(chunk):
                if lang == 'hi':
                    record_text = (
                        f"<b>--- Record {j+1} ---</b>\n"
                        f"• <b>Naam:</b> <code>{record.get('name', 'N/A')}</code>\n"
                        f"• <b>Pita Ka Naam (fname):</b> <code>{record.get('father_name', 'N/A')}</code>\n" # Key changed to father_name
                        f"• <b>Pata:</b> <code>{record.get('address', 'N/A')}</code>\n"
                        f"• <b>Mobile:</b> <code>{record.get('mobile', 'N/A')}</code>\n"
                        f"• <b>Alt Mobile:</b> <code>{record.get('alt_mobile', 'N/A')}</code>\n" # Key changed to alt_mobile
                        f"• <b>Circle:</b> <code>{record.get('circle', 'N/A')}</code>\n"
                    )
                else:
                     record_text = (
                        f"<b>--- Record {j+1} ---</b>\n"
                        f"• <b>Name:</b> <code>{record.get('name', 'N/A')}</code>\n"
                        f"• <b>Father's Name (fname):</b> <code>{record.get('father_name', 'N/A')}</code>\n" # Key changed to father_name
                        f"• <b>Address:</b> <code>{record.get('address', 'N/A')}</code>\n"
                        f"• <b>Mobile:</b> <code>{record.get('mobile', 'N/A')}</code>\n"
                        f"• <b>Alt Mobile:</b> <code>{record.get('alt_mobile', 'N/A')}</code>\n" # Key changed to alt_mobile
                        f"• <b>Circle:</b> <code>{record.get('circle', 'N/A')}</code>\n"
                    )

                message_text += record_text + "\n"
            await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
        
        # ***[सुधार: मेनू दिखाएँ]***
        return await show_main_menu(update, context)

    except (httpx.RequestError, json.JSONDecodeError) as e:
        # JSONDecodeError will now also be caught here if the text trimming or quote fixing fails
        error_msg = str(e)
        if "API returned invalid response text" in error_msg:
             # Provide a generic API error message instead of the long trace
             error_msg = "Invalid/Non-JSON response received from Aadhaar API." 
             
        await update.message.reply_text(get_text(user.id, 'api_error', error=error_msg), parse_mode=ParseMode.HTML)
        update_user_points(user.id, SEARCH_COST) 
        logger.error(f"Aadhaar OSINT API Error: {e}")
        return await cancel_command(update, context) # असफल होने पर cancel करें
    
async def handle_telegram_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """नया: Telegram User ID से OSINT डेटा निकालता है और पॉइंट्स काटता है।"""
    user = update.effective_user
    user_id_to_check = update.message.text.strip()
    
    if not user_id_to_check.isdigit():
        await update.message.reply_text(get_text(user.id, 'invalid_tg_user_id'), parse_mode=ParseMode.HTML)
        return GETTING_TG_USER_ID

    new_points = update_user_points(user.id, -SEARCH_COST)
    await update.message.reply_text(
        get_text(user.id, 'success_deduction', cost=SEARCH_COST, new_points=new_points),
        parse_mode=ParseMode.HTML
    )

    api_url = TG_USER_INFO_API.format(user_id=user_id_to_check)
    lang = load_user_data().get(str(user.id), {}).get('lang', 'hi')

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url)
            api_response = response.json()

        if not api_response.get('success') or not api_response.get('data'):
            await update.message.reply_text(get_text(user.id, 'no_info_found'), parse_mode=ParseMode.HTML)
            update_user_points(user.id, SEARCH_COST) 
            return await cancel_command(update, context)
        
        data = api_response['data']

        # Date Format (Optional, but nice for presentation)
        def format_tg_date(date_str):
            from datetime import datetime
            try:
                # Assuming the format '2025-09-04T06:46:46Z'
                dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
                return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except:
                return date_str # Return as is if parsing fails

        message_text = get_text(user.id, 'tg_info_output', 
            id=data.get('id', 'N/A'),
            first_name=data.get('first_name', 'N/A'),
            last_name=data.get('last_name', 'N/A'),
            is_bot=data.get('is_bot', 'N/A'),
            is_active=data.get('is_active', 'N/A'),
            total_groups=data.get('total_groups', 'N/A'),
            total_msg_count=data.get('total_msg_count', 'N/A'),
            first_msg_date=format_tg_date(data.get('first_msg_date', 'N/A')),
        )
        
        # Add more details that are present in the response
        if lang == 'hi':
            message_text += (
                "• <b>Admin In Groups:</b> <code>{}</code>\n"
                "• <b>Names Count:</b> <code>{}</code>\n"
                "• <b>Last Msg Date:</b> <code>{}</code>\n"
            ).format(
                data.get('adm_in_groups', 'N/A'),
                data.get('names_count', 'N/A'),
                format_tg_date(data.get('last_msg_date', 'N/A'))
            )
        else:
            message_text += (
                "• <b>Admin In Groups:</b> <code>{}</code>\n"
                "• <b>Names Count:</b> <code>{}</code>\n"
                "• <b>Last Msg Date:</b> <code>{}</code>\n"
            ).format(
                data.get('adm_in_groups', 'N/A'),
                data.get('names_count', 'N/A'),
                format_tg_date(data.get('last_msg_date', 'N/A'))
            )

        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
        # ***[सुधार: मेनू दिखाएँ]***
        return await show_main_menu(update, context)

    except (httpx.RequestError, json.JSONDecodeError) as e:
        await update.message.reply_text(get_text(user.id, 'api_error', error=str(e)), parse_mode=ParseMode.HTML)
        update_user_points(user.id, SEARCH_COST) 
        logger.error(f"Telegram OSINT API Error: {e}")
        return await cancel_command(update, context) # असफल होने पर cancel करें
    


# ----------------------------
# 8. रेफर और अर्न हैंडलर
# ----------------------------

async def refer_and_earn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """रेफरल लिंक और पॉइंट जानकारी दिखाता है।"""
    user = update.effective_user
    bot_username = (await context.bot.get_me()).username
    
    referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    points = get_user_points(user.id)
    
    await update.message.reply_text(
        f"{get_text(user.id, 'refer_earn_title')}\n\n"
        f"{get_text(user.id, 'points_info', points=points, cost=SEARCH_COST)}\n"
        f"{get_text(user.id, 'refer_earn_details', bonus=REFERRAL_BONUS, cost=SEARCH_COST)}\n\n"
        f"{get_text(user.id, 'refer_link_prompt', link=referral_link)}",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )
    return SELECTING_ACTION

# ----------------------------
# 9. एडमिन पैनल हैंडलर्स
# ----------------------------

def get_admin_keyboard():
    """एडमिन मेनू के लिए ReplyKeyboardMarkup बनाता है।"""
    return ReplyKeyboardMarkup(
        [
            ["📢 Broadcast Message", "➕ Points Jodein"],
            ["➖ Points Ghataein", "📊 Bot Statistics"],
            ["🏠 Main Menu"] 
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

async def admin_required(update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """जाँच करता है कि यूजर एडमिन है या नहीं।"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
         await update.message.reply_text(get_text(user_id, 'admin_denied'), reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML)
         return False
    return True

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """'/admin' कमांड को हैंडल करता है और Admin Menu दिखाता है।"""
    if not await admin_required(update, context):
        return ConversationHandler.END

    user_id = update.effective_user.id
    
    await update.message.reply_text(
        f"{get_text(user_id, 'admin_panel_title')}\n\n{get_text(user_id, 'admin_prompt')}",
        reply_markup=get_admin_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return SELECTING_ACTION

async def admin_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin ReplyKeyboard के बटन्स को हैंडल करता है।"""
    if not await admin_required(update, context):
        return ConversationHandler.END

    user_id = update.effective_user.id
    text = update.message.text
    
    if "Broadcast Message" in text:
        await update.message.reply_text(get_text(user_id, 'admin_broadcast_start'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return ADMIN_BROADCAST_MSG
    
    elif "Points Jodein" in text:
        await update.message.reply_text(get_text(user_id, 'admin_add_id_prompt'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return ADMIN_ADD_BALANCE_ID

    elif "Points Ghataein" in text:
        await update.message.reply_text(get_text(user_id, 'admin_remove_id_prompt'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return ADMIN_REMOVE_BALANCE_ID

    elif "Bot Statistics" in text:
        return await admin_show_stats(update, context) 

    elif "Main Menu" in text:
        # **यह फ़ंक्शन भी मेन कीबोर्ड दिखाता है**
        return await show_main_menu(update, context) 
    
    await update.message.reply_text(get_text(user_id, 'invalid_option'), reply_markup=get_admin_keyboard(), parse_mode=ParseMode.HTML)
    return SELECTING_ACTION


async def admin_show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """बॉट के स्टैटिस्टिक्स दिखाता है।"""
    data = load_user_data()
    total_users = len(data)
    total_points = sum(user.get('points', 0) for user in data.values())
    total_searches = sum(user.get('searches_done', 0) for user in data.values())
    
    lang = load_user_data().get(str(update.effective_user.id), {}).get('lang', 'hi')
    
    if lang == 'hi':
        stats_text = (
            "📊 <b>Bot Statistics</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Total Users:</b> <code>{total_users}</code>\n"
            f"• <b>Total Points:</b> <code>{total_points}</code>\n"
            f"• <b>Total Searches:</b> <code>{total_searches}</code>\n"
        )
    else:
         stats_text = (
            "📊 <b>Bot Statistics</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Total Users:</b> <code>{total_users}</code>\n"
            f"• <b>Total Points:</b> <code>{total_points}</code>\n"
            f"• <b>Total Searches:</b> <code>{total_searches}</code>\n"
        )
    
    await update.message.reply_text(
        text=stats_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_keyboard() 
    )
    return SELECTING_ACTION

# --- Broadcast Logic ---

async def admin_handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """यूजर से मैसेज लेकर सभी को ब्रॉडकास्ट करता है।"""
    message_to_send = update.message.text
    all_users = load_user_data().keys()
    send_count = 0
    
    await update.message.reply_text(f"📢 <i>{len(all_users)} users ko message bhejna shuru kar raha hoon...</i>", parse_mode=ParseMode.HTML)

    for user_id_str in all_users:
        try:
            if int(user_id_str) != ADMIN_ID:
                await context.bot.send_message(chat_id=int(user_id_str), text=message_to_send, parse_mode=ParseMode.HTML)
                send_count += 1
                await asyncio.sleep(0.05) 
        except Exception as e:
            logger.error(f"Broadcast failed for user {user_id_str}: {e}")

    user_id = update.effective_user.id
    if get_text(user_id, 'lang') == 'hi':
        result_msg = f"✅ <b>Broadcast Poora Hua.</b> <b>{send_count}</b> users tak message pahuncha."
    else:
        result_msg = f"✅ <b>Broadcast Complete.</b> Message reached <b>{send_count}</b> users."

    await update.message.reply_text(
        result_msg,
        reply_markup=get_admin_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return SELECTING_ACTION 

# --- Add Balance Logic ---

async def admin_get_add_balance_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """पॉइंट्स जोड़ने के लिए यूजर आईडी प्राप्त करता है।"""
    user_id = update.effective_user.id
    target_id_str = update.message.text.strip()
    
    if not target_id_str.isdigit():
        await update.message.reply_text(get_text(user_id, 'admin_invalid_id'), parse_mode=ParseMode.HTML)
        return ADMIN_ADD_BALANCE_ID

    context.user_data['target_user_id'] = target_id_str
    
    await update.message.reply_text(get_text(user_id, 'admin_add_points_prompt'), parse_mode=ParseMode.HTML)
    return ADMIN_ADD_BALANCE_POINTS

async def admin_get_add_balance_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """पॉइंट्स की संख्या लेकर यूजर को पॉइंट्स देता है।"""
    admin_id = update.effective_user.id
    points_str = update.message.text.strip()
    user_id_str = context.user_data.get('target_user_id')
    
    if not points_str.isdigit():
        await update.message.reply_text(get_text(admin_id, 'admin_invalid_points'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return ADMIN_ADD_BALANCE_POINTS

    points = int(points_str)
    target_id = int(user_id_str)
    
    # पॉइंट्स अपडेट करें
    new_points = update_user_points(target_id, points)
    
    await update.message.reply_text(
        get_text(admin_id, 'admin_add_success', points=points, id=target_id, new_points=new_points),
        reply_markup=get_admin_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    try:
        await context.bot.send_message(
            chat_id=target_id, 
            text=get_text(target_id, 'admin_notify_add', points=points, new_points=new_points),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Could not notify user {target_id}: {e}")

    return SELECTING_ACTION 

# --- Remove Balance Logic ---

async def admin_get_remove_balance_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """पॉइंट्स हटाने के लिए यूजर आईडी प्राप्त करता है।"""
    user_id = update.effective_user.id
    target_id_str = update.message.text.strip()
    
    if not target_id_str.isdigit():
        await update.message.reply_text(get_text(user_id, 'admin_invalid_id'), parse_mode=ParseMode.HTML)
        return ADMIN_REMOVE_BALANCE_ID

    context.user_data['target_user_id'] = target_id_str
    
    await update.message.reply_text(get_text(user_id, 'admin_remove_points_prompt'), parse_mode=ParseMode.HTML)
    return ADMIN_REMOVE_BALANCE_POINTS


async def admin_get_remove_balance_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """पॉइंट्स की संख्या लेकर यूजर से पॉइंट्स हटाता है।"""
    admin_id = update.effective_user.id
    points_str = update.message.text.strip()
    user_id_str = context.user_data.get('target_user_id')

    if not points_str.isdigit():
        await update.message.reply_text(get_text(admin_id, 'admin_invalid_points'), reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        return ADMIN_REMOVE_BALANCE_POINTS

    points = int(points_str)
    target_id = int(user_id_str)

    # पॉइंट्स अपडेट करें (नेगेटिव वैल्यू पास करें)
    new_points = update_user_points(target_id, -points)
    
    await update.message.reply_text(
        get_text(admin_id, 'admin_remove_success', points=points, id=target_id, new_points=new_points),
        reply_markup=get_admin_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    try:
        await context.bot.send_message(
            chat_id=target_id, 
            text=get_text(target_id, 'admin_notify_remove', points=points, new_points=new_points),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Could not notify user {target_id}: {e}")

    return SELECTING_ACTION 


# ----------------------------
# 10. मुख्य फंक्शन (main)
# ----------------------------

def main() -> None:
    """बॉट को शुरू करता है।"""
    logger.info("Bot application shuru ho raha hai...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # /start और Inline Callback Handler
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(check_sub_callback, pattern='^check_sub$'))
    application.add_handler(CallbackQueryHandler(select_language_callback, pattern='^lang_(hi|en)$')) # नया: भाषा चयन हैंडलर

    # मेनू बटन के लिए फ़िल्टर (नए बटन जोड़े गए)
    MENU_BUTTON_FILTER = filters.Regex("^(🔍 Number to Info|🚗 Vehicle Info|🪪 Aadhaar Info|👤 Telegram User Info|🤑 Refer and Earn|🌎 Change Language)$")
    # एडमिन मेनू बटन के लिए फ़िल्टर 
    ADMIN_MENU_FILTER = filters.Regex("^(📢 Broadcast Message|➕ Points Jodein|➖ Points Ghataein|📊 Bot Statistics|🏠 Main Menu)$")

    # 1. Main Conversation Handler for OSINT/Menu
    main_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            MessageHandler(MENU_BUTTON_FILTER & ~filters.COMMAND, handle_menu_selection) 
        ],
        
        states={
            # नया स्टेट
            SELECTING_LANGUAGE: [
                CallbackQueryHandler(select_language_callback, pattern='^lang_(hi|en)$'),
            ],
            SELECTING_ACTION: [
                MessageHandler(MENU_BUTTON_FILTER & ~filters.COMMAND, handle_menu_selection),
                CommandHandler("cancel", cancel_command)
            ],
            GETTING_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number_info),
                CommandHandler("cancel", cancel_command)
            ],
            GETTING_VEHICLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vehicle_info),
                CommandHandler("cancel", cancel_command)
            ],
            GETTING_AADHAAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_aadhaar_info),
                CommandHandler("cancel", cancel_command)
            ],
            GETTING_TG_USER_ID: [ # नया TG User Info स्टेट
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_info),
                CommandHandler("cancel", cancel_command)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    # 2. Admin Conversation Handler 
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_command, filters.User(ADMIN_ID))],
        
        states={
            SELECTING_ACTION: [ 
                MessageHandler(ADMIN_MENU_FILTER & ~filters.COMMAND, admin_menu_selection),
            ],
            ADMIN_BROADCAST_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handle_broadcast_message),
            ],
            ADMIN_ADD_BALANCE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_add_balance_id),
            ],
            ADMIN_ADD_BALANCE_POINTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_add_balance_points),
            ],
            ADMIN_REMOVE_BALANCE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_remove_balance_id),
            ],
            ADMIN_REMOVE_BALANCE_POINTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_remove_balance_points),
            ],
        },
        fallbacks=[CommandHandler("admincancel", admin_command, filters.User(ADMIN_ID))],
        per_user=True,
        per_chat=False,
    )
    
    application.add_handler(main_conv_handler)
    application.add_handler(admin_conv_handler)

    logger.info("Bot polling shuru ho raha hai...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    if ADMIN_ID == 7420417469:
        logger.warning("🚨 WARNING: ADMIN_ID 7420417469 par set hai. Kripya ise badal dein!")
    main()