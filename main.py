from telegram import (
    Update,
)
from telegram.ext import (
    # PicklePersistence,
    ChatMemberHandler,
    ChatJoinRequestHandler,
    CallbackQueryHandler,
    ApplicationBuilder,
    CommandHandler,
    InvalidCallbackData
)

import shutil
from random import randint

from constants import *
from admin import *
from user import *
from general import error_handler, post_init

def main() -> None:
    # persistence = PicklePersistence(filepath="arbitrarycallbackdatabot",
    #                                     update_interval=0,
    #                                         on_flush=True)
    app = (ApplicationBuilder()
           .token(TOKEN)
          #.persistence(persistence)
          #.arbitrary_callback_data(True) 
           .post_init(post_init)
           .build())
    
    # user   
    app.add_handler(conv_first_run)
    app.add_handler(conv_solotest)
    app.add_handler(conv_review)    
    app.add_handler(CallbackQueryHandler(bonus_menu,
                                            pattern=f"^{GET_BONUSES}$"))
    app.add_handler(conv_check)
    app.add_handler(CallbackQueryHandler(follow,
                                            pattern=f"^{FOLLOW}$"))
    app.add_handler(CallbackQueryHandler(referral,
                                            pattern=f"^{REFERRAL}$"))
    app.add_handler(conv_support)
    app.add_handler(CallbackQueryHandler(raffle_entry,
                                         pattern=f"^{RAFFLE_ENTRY}$"))

    # web app
    app.add_handler(CallbackQueryHandler(exchange, 
                                         pattern=f"^(exchange-)"))
    app.add_handler(CallbackQueryHandler(fall, pattern="999"))

    # admin
    app.add_handler(CommandHandler("edit", edit))

    app.add_handler(conv_applications)
    app.add_handler(conv_reviews)
    app.add_handler(conv_bonuses)
    app.add_handler(conv_add_admin)
    app.add_handler(conv_del_admin)
    app.add_handler(conv_newsletter)
    app.add_handler(conv_promocodes)
    app.add_handler(CallbackQueryHandler(review_confirm_accept,
                                         pattern=f"^({REVIEW_CONFIRM_NOTIFICATION}-)"))

    # admin/user start
    app.add_handler(CallbackQueryHandler(admin, pattern=f"^{ADMIN_MENU}$")) # Должен быть в конце
    app.add_handler(CallbackQueryHandler(start, pattern=f"^{USER_MENU}$")) # Должен быть в конце
    app.add_handler(CommandHandler('admin', admin)) # Должен быть в конце
    app.add_handler(CommandHandler('start', start)) # Должен быть в конце

    # other
    app.add_error_handler(error_handler)
    app.add_handler(ChatMemberHandler(greet_chat_members,
                                        ChatMemberHandler.CHAT_MEMBER,
                                            chat_id=CHANNEL_ID))
    app.add_handler(
        CallbackQueryHandler(handle_invalid_button, pattern=InvalidCallbackData)
    )

    # Должен быть последним, дабы принять все непринятые доселе кнопки:
    # app.add_handler(CallbackQueryHandler(everything_else))

    # run
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()