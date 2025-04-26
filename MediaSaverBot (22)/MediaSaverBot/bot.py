import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import tempfile
from flask import Flask
from models import init_db

from config import (
    BOT_TOKEN, WELCOME_MESSAGE, DOWNLOAD_SUCCESS_MESSAGE, 
    INVALID_URL_MESSAGE, PROCESSING_MESSAGE, ERROR_MESSAGE,
    DONATION_TEXT, DONATION_URL
)
from url_validator import get_url_type
from downloaders import (
    download_youtube_video, 
    download_instagram_video, 
    download_tiktok_video,
    download_twitter_video,
    download_facebook_video,
    DownloadError
)
from keyboards import get_donation_keyboard
from service import get_or_create_user, record_download, record_donation_click, get_user_stats

# Initialize Flask for database
bot_app = Flask(__name__)
init_db(bot_app)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(WELCOME_MESSAGE)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    await update.message.reply_text(WELCOME_MESSAGE)

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send donation information when the command /donate is issued."""
    donation_message = DONATION_TEXT.format(donation_url=DONATION_URL)
    
    # Get donation keyboard with URL validation
    donation_keyboard = get_donation_keyboard(DONATION_URL)
    
    # Send with or without keyboard based on if keyboard creation was successful
    if donation_keyboard:
        await update.message.reply_text(
            donation_message,
            reply_markup=donation_keyboard
        )
    else:
        await update.message.reply_text(donation_message)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the URL received from the user."""
    url = update.message.text.strip()
    logger.info(f"Received URL: {url}")
    
    # Check if the URL is valid
    url_type = get_url_type(url)
    
    if not url_type:
        logger.info(f"Invalid URL rejected: {url}")
        await update.message.reply_text(INVALID_URL_MESSAGE)
        return
        
    # Get or create user in database
    try:
        with bot_app.app_context():
            user_db = get_or_create_user(update)
            if not user_db:
                logger.error("Failed to get or create user in database")
    except Exception as e:
        logger.error(f"Database error when creating user: {str(e)}")
        user_db = None
    
    # Send processing message
    processing_msg = await update.message.reply_text(PROCESSING_MESSAGE)
    
    try:
        # Log the download attempt
        logger.info(f"Attempting to download from {url_type}: {url}")
        
        # Initialize video_path variable
        video_path = None
        
        # Download the video based on the URL type
        if url_type == 'youtube':
            video_path = download_youtube_video(url)
        elif url_type == 'instagram':
            video_path = download_instagram_video(url)
        elif url_type == 'tiktok':
            video_path = download_tiktok_video(url)
        elif url_type == 'twitter':
            video_path = download_twitter_video(url)
        elif url_type == 'facebook':
            video_path = download_facebook_video(url)
            
        # Make sure we have a valid video path
        if video_path is None:
            raise DownloadError(f"Couldn't download video from {url_type}: {url}")
            
        # Check if the video file exists and is readable
        if not os.path.exists(video_path):
            raise DownloadError("The downloaded file could not be found.")
            
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024*1024)
        logger.info(f"Successfully downloaded video, file size: {file_size_mb:.2f} MB")
        
        # Check if the file isn't too large for Telegram
        max_size_mb = 50
        if file_size > max_size_mb * 1024 * 1024:
            # Record failed download in database
            with bot_app.app_context():
                if user_db:
                    record_download(
                        user_db.user_id, 
                        url, 
                        url_type, 
                        file_size_mb, 
                        'failed', 
                        f"Video too large to send (limit: {max_size_mb}MB)"
                    )
            raise DownloadError(f"The video is too large to send via Telegram (limit: {max_size_mb}MB).")
        
        # Send the video file
        try:
            with open(video_path, 'rb') as video_file:
                # Get donation keyboard with URL validation
                donation_keyboard = get_donation_keyboard(DONATION_URL)
                
                # Send video with or without keyboard based on if keyboard creation was successful
                if donation_keyboard:
                    await update.message.reply_video(
                        video=video_file,
                        caption=DOWNLOAD_SUCCESS_MESSAGE,
                        reply_markup=donation_keyboard
                    )
                else:
                    # If keyboard creation failed, send without keyboard
                    await update.message.reply_video(
                        video=video_file,
                        caption=DOWNLOAD_SUCCESS_MESSAGE
                    )
            logger.info("Video successfully sent to user")
            
            # Record successful download in database
            try:
                with bot_app.app_context():
                    if user_db:
                        record_download(
                            user_db.user_id, 
                            url, 
                            url_type, 
                            file_size_mb, 
                            'success'
                        )
            except Exception as db_err:
                logger.error(f"Failed to record successful download in database: {str(db_err)}")
                    
        except Exception as e:
            logger.error(f"Error sending video: {str(e)}")
            # Record failed download in database
            try:
                with bot_app.app_context():
                    if user_db:
                        record_download(
                            user_db.user_id, 
                            url, 
                            url_type, 
                            file_size_mb, 
                            'failed', 
                            f"Could not send video: {str(e)}"
                        )
            except Exception as db_err:
                logger.error(f"Failed to record failed download in database: {str(db_err)}")
            raise DownloadError(f"Could not send video: {str(e)}")
        
        # Delete the processing message
        await processing_msg.delete()
        
        # Clean up - remove the temporary file
        try:
            os.remove(video_path)
            # If the file is in a temporary directory, try to remove the directory too
            temp_dir = os.path.dirname(video_path)
            if temp_dir.startswith(tempfile.gettempdir()):
                os.rmdir(temp_dir)
            logger.info("Temporary files cleaned up successfully")
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"Failed to clean up temporary files: {str(e)}")
            
    except DownloadError as e:
        error_message = str(e)
        logger.error(f"Download error: {error_message}")
        
        # Record failed download in database
        try:
            with bot_app.app_context():
                if user_db:
                    record_download(
                        user_db.user_id, 
                        url, 
                        url_type, 
                        None, 
                        'failed', 
                        error_message
                    )
        except Exception as db_err:
            logger.error(f"Failed to record download in database: {str(db_err)}")
        
        # Customize error messages for better user experience
        user_friendly_message = ERROR_MESSAGE
        
        if "is private" in error_message.lower():
            user_friendly_message = "😔 Sorry, I can't download videos from private accounts. The account needs to be public."
        elif "is too large" in error_message.lower():
            user_friendly_message = "😔 Sorry, this video is too large to send via Telegram. Telegram has a 50MB size limit."
        elif "does not contain a video" in error_message.lower():
            user_friendly_message = "😔 This post doesn't contain a video. I can only download video content."
        elif "could not load video information" in error_message.lower():
            user_friendly_message = "😔 I couldn't load information about this video. It might be private or restricted."
        elif "no suitable video streams" in error_message.lower():
            user_friendly_message = "😔 No suitable video format found. The video might be unavailable or protected."
        
        # Add the technical details for debugging
        detailed_message = f"{user_friendly_message}\n\nDetails: {error_message}"
        await processing_msg.edit_text(detailed_message)
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        
        # Record failed download in database
        try:
            with bot_app.app_context():
                if user_db:
                    record_download(
                        user_db.user_id, 
                        url, 
                        url_type if url_type else 'unknown', 
                        None, 
                        'failed', 
                        f"Unexpected error: {str(e)}"
                    )
        except Exception as db_err:
            logger.error(f"Failed to record download in database: {str(db_err)}")
                
        await processing_msg.edit_text(f"{ERROR_MESSAGE}\n\nAn unexpected error occurred. Please try again later.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline buttons."""
    query = update.callback_query
    await query.answer()
    
    # Note: We can't track donation clicks via callback_data since 
    # InlineKeyboardButton can't have both url and callback_data.
    # If we want to track clicks, we'd need to create a custom URL shortener/redirect service.

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def run_bot():
    """Run the bot."""
    # Check if the bot token is set
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("donate", donate_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
