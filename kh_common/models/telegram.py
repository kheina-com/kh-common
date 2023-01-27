from datetime import datetime, timedelta
from enum import Enum
from typing import List, Literal, Optional, Type, Union

from pydantic import BaseModel, Field, HttpUrl


################################################## RESPONSE MODELS ##################################################


class WebAppInfo(BaseModel) :
	url: str
	"""An HTTPS URL of a Web App to be opened with additional data as specified in [Initializing Web Apps](https://core.telegram.org/bots/webapps#initializing-web-apps)"""


class LoginUrl(BaseModel) :
	url: HttpUrl
	"""An HTTPS URL to be opened with user authorization data added to the query string when the button is pressed. If the user refuses to provide authorization data, the original URL without information about the user will be opened. The data added is the same as described in Receiving authorization data.

	NOTE: You must always check the hash of the received data to verify the authentication and the integrity of the data as described in Checking authorization."""
	forward_text: Optional[str]
	"""New text of the button in forwarded messages."""
	bot_username: Optional[str]
	"""Username of a bot, which will be used for user authorization. See Setting up a bot for more details. If not specified, the current bot's username will be assumed. The url's domain must be the same as the domain linked with the bot. See Linking your domain to the bot for more details."""
	request_write_access: Optional[bool]
	"""Pass True to request the permission for your bot to send messages to the user."""


class CallbackGame(BaseModel) :
	user_id: int
	"""User identifier"""
	score: int
	"""New score, must be non-negative"""
	force: Optional[bool]
	"""Pass True if the high score is allowed to decrease. This can be useful when fixing mistakes or banning cheaters"""
	disable_edit_message: Optional[bool]
	"""Pass True if the game message should not be automatically edited to include the current scoreboard"""
	chat_id: Optional[int]
	"""Required if inline_message_id is not specified. Unique identifier for the target chat"""
	message_id: Optional[int]
	"""Required if inline_message_id is not specified. Identifier of the sent message"""
	inline_message_id: Optional[str]
	"""Required if chat_id and message_id are not specified. Identifier of the inline message"""


class InlineKeyboardButton(BaseModel) :
	text: str
	"""Label text on the button"""
	url: Optional[str]
	"""HTTP or tg:// URL to be opened when the button is pressed. Links tg://user?id=<user_id> can be used to mention a user by their ID without using a username, if this is allowed by their privacy settings."""
	callback_data: Optional[str]
	"""Data to be sent in a callback query to the bot when button is pressed, 1-64 bytes"""
	web_app: Optional[WebAppInfo]
	"""Description of the Web App that will be launched when the user presses the button. The Web App will be able to send an arbitrary message on behalf of the user using the method answerWebAppQuery. Available only in private chats between a user and the bot."""
	login_url: Optional[LoginUrl]
	"""An HTTPS URL used to automatically authorize the user. Can be used as a replacement for the Telegram Login Widget."""
	switch_inline_query: Optional[str]
	"""If set, pressing the button will prompt the user to select one of their chats, open that chat and insert the bot's username and the specified inline query in the input field. May be empty, in which case just the bot's username will be inserted.

	Note: This offers an easy way for users to start using your bot in inline mode when they are currently in a private chat with it. Especially useful when combined with switch_pm… actions - in this case the user will be automatically returned to the chat they switched from, skipping the chat selection screen."""
	switch_inline_query_current_chat: Optional[str]
	"""If set, pressing the button will insert the bot's username and the specified inline query in the current chat's input field. May be empty, in which case only the bot's username will be inserted.

	This offers a quick way for the user to open your bot in inline mode in the same chat - good for selecting something from multiple options."""
	callback_game: Optional[CallbackGame]
	"""Description of the game that will be launched when the user presses the button."""
	pay: Optional[bool]
	"""Specify True, to send a Pay button.

	NOTE: This type of button must always be the first button in the first row."""


class InlineKeyboardMarkup(BaseModel) :
	inline_keyboard: List[List[InlineKeyboardButton]]
	"""Array of button rows, each represented by an Array of InlineKeyboardButton objects"""


class KeyboardButtonPollType(BaseModel) :
	type: Optional[str]
	"""If quiz is passed, the user will be allowed to create only polls in the quiz mode. If regular is passed, only regular polls will be allowed. Otherwise, the user will be allowed to create a poll of any type."""


class KeyboardButton(BaseModel) :
	text: str
	"""Text of the button. If none of the optional fields are used, it will be sent as a message when the button is pressed"""
	request_contact: Optional[bool]
	"""If True, the user's phone number will be sent as a contact when the button is pressed. Available in private chats only."""
	request_location: Optional[bool]
	"""If True, the user's current location will be sent when the button is pressed. Available in private chats only."""
	request_poll: KeyboardButtonPollType
	"""If specified, the user will be asked to create a poll and send it to the bot when the button is pressed. Available in private chats only."""
	web_app: Optional[WebAppInfo]
	"""If specified, the described Web App will be launched when the button is pressed. The Web App will be able to send a “web_app_data” service message. Available in private chats only."""


class ReplyKeyboardMarkup(BaseModel) :
	keyboard: List[List[KeyboardButton]]
	"""Array of button rows, each represented by an Array of KeyboardButton objects"""
	is_persistent: Optional[bool]
	"""Requests clients to always show the keyboard when the regular keyboard is hidden. Defaults to false, in which case the custom keyboard can be hidden and opened with a keyboard icon."""
	resize_keyboard: Optional[bool]
	"""Requests clients to resize the keyboard vertically for optimal fit (e.g., make the keyboard smaller if there are just two rows of buttons). Defaults to false, in which case the custom keyboard is always of the same height as the app's standard keyboard."""
	one_time_keyboard: Optional[bool]
	"""Requests clients to hide the keyboard as soon as it's been used. The keyboard will still be available, but clients will automatically display the usual letter-keyboard in the chat - the user can press a special button in the input field to see the custom keyboard again. Defaults to false."""
	input_field_placeholder: Optional[str]
	"""The placeholder to be shown in the input field when the keyboard is active; 1-64 characters"""
	selective: Optional[bool]
	"""Use this parameter if you want to show the keyboard to specific users only. Targets: 1) users that are @mentioned in the text of the Message object; 2) if the bot's message is a reply (has reply_to_message_id), sender of the original message.

	Example: A user requests to change the bot's language, bot replies to the request with a keyboard to select the new language. Other users in the group don't see the keyboard."""


class ReplyKeyboardRemove(BaseModel) :
	remove_keyboard: Literal[True]
	"""Requests clients to remove the custom keyboard (user will not be able to summon this keyboard; if you want to hide the keyboard from sight but keep it accessible, use one_time_keyboard in ReplyKeyboardMarkup)"""
	selective: Optional[bool]
	"""Use this parameter if you want to remove the keyboard for specific users only. Targets: 1) users that are @mentioned in the text of the Message object; 2) if the bot's message is a reply (has reply_to_message_id), sender of the original message.

	Example: A user votes in a poll, bot returns confirmation message in reply to the vote and removes the keyboard for that user, while still showing the keyboard with poll options to users who haven't voted yet."""


class ForceReply(BaseModel) :
	force_reply: Literal[True]
	"""Shows reply interface to the user, as if they manually selected the bot's message and tapped 'Reply'"""
	input_field_placeholder: Optional[str]
	"""The placeholder to be shown in the input field when the reply is active; 1-64 characters"""
	selective: Optional[bool]
	"""Use this parameter if you want to force reply from specific users only. Targets: 1) users that are @mentioned in the text of the Message object; 2) if the bot's message is a reply (has reply_to_message_id), sender of the original message."""

################################################## UPDATE MODELS ##################################################


class User(BaseModel) :
	id: int
	"""Unique identifier for this user or bot. This number may have more than 32 significant bits and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a 64-bit integer or double-precision float type are safe for storing this identifier."""
	is_bot: bool
	"""True, if this user is a bot"""
	first_name: str
	"""User's or bot's first name"""
	last_name: Optional[str]
	"""User's or bot's last name"""
	username: Optional[str]
	"""User's or bot's username"""
	language_code: Optional[str]
	"""IETF language tag of the user's language"""
	is_premium: Optional[bool]
	"""True, if this user is a Telegram Premium user"""
	added_to_attachment_menu: Optional[bool]
	"""True, if this user added the bot to the attachment menu"""
	can_join_groups: Optional[bool]
	"""True, if the bot can be invited to groups. Returned only in getMe."""
	can_read_all_group_messages: Optional[bool]
	"""True, if privacy mode is disabled for the bot. Returned only in getMe."""
	supports_inline_queries: Optional[bool]
	"""True, if the bot supports inline queries. Returned only in getMe."""


class ChatPhoto(BaseModel) :
	small_file_id: str
	"""File identifier of small (160x160) chat photo. This file_id can be used only for photo download and only for as long as the photo is not changed."""
	small_file_unique_id: str
	"""Unique file identifier of small (160x160) chat photo, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	big_file_id: str
	"""File identifier of big (640x640) chat photo. This file_id can be used only for photo download and only for as long as the photo is not changed."""
	big_file_unique_id: str
	"""Unique file identifier of big (640x640) chat photo, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""


class ChatPermissions(BaseModel) :
	can_send_messages: Optional[bool]
	"""True, if the user is allowed to send text messages, contacts, locations and venues"""
	can_send_media_messages: Optional[bool]
	"""True, if the user is allowed to send audios, documents, photos, videos, video notes and voice notes, implies can_send_messages"""
	can_send_polls: Optional[bool]
	"""True, if the user is allowed to send polls, implies can_send_messages"""
	can_send_other_messages: Optional[bool]
	"""True, if the user is allowed to send animations, games, stickers and use inline bots, implies can_send_media_messages"""
	can_add_web_page_previews: Optional[bool]
	"""True, if the user is allowed to add web page previews to their messages, implies can_send_media_messages"""
	can_change_info: Optional[bool]
	"""True, if the user is allowed to change the chat title, photo and other settings. Ignored in public supergroups"""
	can_invite_users: Optional[bool]
	"""True, if the user is allowed to invite new users to the chat"""
	can_pin_messages: Optional[bool]
	"""True, if the user is allowed to pin messages. Ignored in public supergroups"""
	can_manage_topics: Optional[bool]
	"""True, if the user is allowed to create forum topics. If omitted defaults to the value of can_pin_messages"""


class Location(BaseModel) :
	longitude: float
	"""Longitude as defined by sender"""
	latitude: float
	"""Latitude as defined by sender"""
	horizontal_accuracy: Optional[float]
	"""The radius of uncertainty for the location, measured in meters; 0-1500"""
	live_period: Optional[timedelta]
	"""Time relative to the message sending date, during which the location can be updated; in seconds. For active live locations only."""
	heading: Optional[int]
	"""The direction in which user is moving, in degrees; 1-360. For active live locations only."""
	proximity_alert_radius: Optional[int]
	"""The maximum distance for proximity alerts about approaching another chat member, in meters. For sent live locations only."""


class ChatLocation(BaseModel) :
	location: Location
	"""The location to which the supergroup is connected. Can't be a live location."""
	address: str
	"""Location address; 1-64 characters, as defined by the chat owner"""


class ChatType(Enum) :
	# Type of chat, can be either 'private', 'group', 'supergroup', 'channel', or 'sender' for a private chat with the inline query sender
	sender: str = 'sender'
	private: str = 'private'
	group: str = 'group'
	supergroup: str = 'supergroup'
	channel: str = 'channel'


class Chat(BaseModel) :
	id: int
	"""Unique identifier for this chat. This number may have more than 32 significant bits and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this identifier."""
	type: ChatType
	"""Type of chat, can be either 'private', 'group', 'supergroup' or 'channel'"""
	title: Optional[str]
	"""Title, for supergroups, channels and group chats"""
	username: Optional[str]
	"""Username, for private chats, supergroups and channels if available"""
	first_name: Optional[str]
	"""First name of the other party in a private chat"""
	last_name: Optional[str]
	"""Last name of the other party in a private chat"""
	is_forum: Optional[bool]
	"""True, if the supergroup chat is a forum (has topics enabled)"""
	photo: Optional[ChatPhoto]
	"""Chat photo. Returned only in getChat."""
	active_usernames: Optional[str]
	"""If non-empty, the list of all active chat usernames; for private chats, supergroups and channels. Returned only in getChat."""
	emoji_status_custom_emoji_id: Optional[str]
	"""Custom emoji identifier of emoji status of the other party in a private chat. Returned only in getChat."""
	bio: Optional[str]
	"""Bio of the other party in a private chat. Returned only in getChat."""
	has_private_forwards: Optional[bool]
	"""True, if privacy settings of the other party in the private chat allows to use tg://user?id=<user_id> links only in chats with the user. Returned only in getChat."""
	has_restricted_voice_and_video_messages: Optional[bool]
	"""True, if the privacy settings of the other party restrict sending voice and video note messages in the private chat. Returned only in getChat."""
	join_to_send_messages: Optional[bool]
	"""True, if users need to join the supergroup before they can send messages. Returned only in getChat."""
	join_by_request: Optional[bool]
	"""True, if all users directly joining the supergroup need to be approved by supergroup administrators. Returned only in getChat."""
	description: Optional[str]
	"""Description, for groups, supergroups and channel chats. Returned only in getChat."""
	invite_link: Optional[HttpUrl]
	"""Primary invite link, for groups, supergroups and channel chats. Returned only in getChat."""
	pinned_message: Optional['Message']
	"""The most recent pinned message (by sending date). Returned only in getChat."""
	permissions: Optional[ChatPermissions]
	"""Default chat member permissions, for groups and supergroups. Returned only in getChat."""
	slow_mode_delay: Optional[int]
	"""For supergroups, the minimum allowed delay between consecutive messages sent by each unpriviledged user; in seconds. Returned only in getChat."""
	message_auto_delete_time: Optional[int]
	"""The time after which all messages sent to the chat will be automatically deleted; in seconds. Returned only in getChat."""
	has_aggressive_anti_spam_enabled: Optional[bool]
	"""True, if aggressive anti-spam checks are enabled in the supergroup. The field is only available to chat administrators. Returned only in getChat."""
	has_hidden_members: Optional[bool]
	"""True, if non-administrators can only get the list of bots and administrators in the chat. Returned only in getChat."""
	has_protected_content: Optional[bool]
	"""True, if messages from the chat can't be forwarded to other chats. Returned only in getChat."""
	sticker_set_name: Optional[str]
	"""For supergroups, name of group sticker set. Returned only in getChat."""
	can_set_sticker_set: Optional[bool]
	"""True, if the bot can change the group sticker set. Returned only in getChat."""
	linked_chat_id: Optional[int]
	"""Unique identifier for the linked chat, i.e. the discussion group identifier for a channel and vice versa; for supergroups and channel chats. This identifier may be greater than 32 bits and some programming languages may have difficulty/silent defects in interpreting it. But it is smaller than 52 bits, so a signed 64 bit integer or double-precision float type are safe for storing this identifier. Returned only in getChat."""
	location: Optional[ChatLocation]
	"""For supergroups, the location to which the supergroup is connected. Returned only in getChat."""


class MessageEntityType(Enum) :
	mention: str = 'mention'
	"""@username"""
	hashtag: str = 'hashtag'
	"""#hashtag"""
	cashtag: str = 'cashtag'
	"""$USD"""
	bot_command: str = 'bot_command'
	"""/start@jobs_bot"""
	url: HttpUrl = 'url'
	"""https://telegram.org"""
	email: str = 'email'
	"""do-not-reply@telegram.org"""
	phone_number: str = 'phone_number'
	"""+1-212-555-0123"""
	bold: str = 'bold'
	"""bold text"""
	italic: str = 'italic'
	"""italic text"""
	underline: str = 'underline'
	"""underlined text"""
	strikethrough: str = 'strikethrough'
	"""strikethrough text"""
	spoiler: str = 'spoiler'
	"""spoiler message"""
	code: str = 'code'
	"""monowidth string"""
	pre: str = 'pre'
	"""monowidth block"""
	text_link: HttpUrl = 'text_link'
	"""for clickable text URLs"""
	text_mention: str = 'text_mention'
	"""for users without usernames"""
	custom_emoji: str = 'custom_emoji'
	"""for inline custom emoji stickers"""


class MessageEntity(BaseModel) :
	type: MessageEntityType
	"""Type of the entity."""
	offset: int
	"""Offset in UTF-16 code units to the start of the entity"""
	length: int
	"""Length of the entity in UTF-16 code units"""
	url: Optional[HttpUrl]
	"""For 'text_link' only, URL that will be opened after user taps on the text"""
	user: Optional[User]
	"""For 'text_mention' only, the mentioned user"""
	language: Optional[str]
	"""For 'pre' only, the programming language of the entity text"""
	custom_emoji_id: Optional[str]
	"""For 'custom_emoji' only, unique identifier of the custom emoji. Use getCustomEmojiStickers to get full information about the sticker"""


class PhotoSize(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	width: int
	"""Photo width"""
	height: int
	"""Photo height"""
	file_size: Optional[int]
	"""File size in bytes"""


class Animation(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	width: int
	"""Video width as defined by sender"""
	height: int
	"""Video height as defined by sender"""
	duration: int
	"""Duration of the video in seconds as defined by sender"""
	thumb: Optional[PhotoSize]
	"""Animation thumbnail as defined by sender"""
	file_name: Optional[str]
	"""Original animation filename as defined by sender"""
	mime_type: Optional[str]
	"""MIME type of the file as defined by sender"""
	file_size: Optional[int]
	"""File size in bytes. It can be bigger than 2^31 and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this value."""


class Audio(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	duration: timedelta
	"""Duration of the audio in seconds as defined by sender"""
	performer: Optional[str]
	"""Performer of the audio as defined by sender or by audio tags"""
	title: Optional[str]
	"""Title of the audio as defined by sender or by audio tags"""
	file_name: Optional[str]
	"""Original filename as defined by sender"""
	mime_type: Optional[str]
	"""MIME type of the file as defined by sender"""
	file_size: Optional[int]
	"""File size in bytes. It can be bigger than 2^31 and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this value."""
	thumb: Optional[PhotoSize]
	"""Thumbnail of the album cover to which the music file belongs"""


class Document(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	thumb: Optional[PhotoSize]
	"""Document thumbnail as defined by sender"""
	file_name: Optional[str]
	"""Original filename as defined by sender"""
	mime_type: Optional[str]
	"""MIME type of the file as defined by sender"""
	file_size: Optional[int]
	"""File size in bytes. It can be bigger than 2^31 and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this value."""


class MaskPosition(BaseModel) :
	point: str
	"""The part of the face relative to which the mask should be placed. One of “forehead”, “eyes”, “mouth”, or “chin”."""
	x_shift: float
	"""Shift by X-axis measured in widths of the mask scaled to the face size, from left to right. For example, choosing -1.0 will place mask just to the left of the default mask position."""
	y_shift: float
	"""Shift by Y-axis measured in heights of the mask scaled to the face size, from top to bottom. For example, 1.0 will place the mask just below the default mask position."""
	scale: float
	"""Mask scaling coefficient. For example, 2.0 means double size."""


class File(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	file_size: Optional[int]
	"""File size in bytes. It can be bigger than 2^31 and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this value."""
	file_path: Optional[str]
	"""File path. Use https://api.telegram.org/file/bot<token>/<file_path> to get the file."""


class Sticker(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	type: str
	"""Type of the sticker, currently one of “regular”, “mask”, “custom_emoji”. The type of the sticker is independent from its format, which is determined by the fields is_animated and is_video."""
	width: int
	"""Sticker width"""
	height: int
	"""Sticker height"""
	is_animated: bool
	"""True, if the sticker is animated"""
	is_video: bool
	"""True, if the sticker is a video sticker"""
	thumb: Optional[PhotoSize]
	"""Sticker thumbnail in the .WEBP or .JPG format"""
	emoji: Optional[str]
	"""Emoji associated with the sticker"""
	set_name: Optional[str]
	"""Name of the sticker set to which the sticker belongs"""
	premium_animation: Optional[File]
	"""For premium regular stickers, premium animation for the sticker"""
	mask_position: Optional[MaskPosition]
	"""For mask stickers, the position where the mask should be placed"""
	custom_emoji_id: Optional[str]
	"""For custom emoji stickers, unique identifier of the custom emoji"""
	file_size: Optional[int]
	"""File size in bytes"""


class Video(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	width: int
	"""Video width as defined by sender"""
	height: int
	"""Video height as defined by sender"""
	duration: int
	"""Duration of the video in seconds as defined by sender"""
	thumb: Optional[PhotoSize]
	"""Video thumbnail"""
	file_name: Optional[str]
	"""Original filename as defined by sender"""
	mime_type: Optional[str]
	"""MIME type of the file as defined by sender"""
	file_size: Optional[int]
	"""File size in bytes. It can be bigger than 2^31 and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this value."""


class VideoNote(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	length: int
	"""Video width and height (diameter of the video message) as defined by sender"""
	duration: timedelta
	"""Duration of the video in seconds as defined by sender"""
	thumb: Optional[PhotoSize]
	"""Video thumbnail"""
	file_size: Optional[int]
	"""File size in bytes"""


class Voice(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	duration: timedelta
	"""Duration of the audio in seconds as defined by sender"""
	mime_type: Optional[str]
	"""MIME type of the file as defined by sender"""
	file_size: Optional[int]
	"""File size in bytes. It can be bigger than 2^31 and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this value."""


class Contact(BaseModel) :
	phone_number: str
	"""Contact's phone number"""
	first_name: str
	"""Contact's first name"""
	last_name: Optional[str]
	"""Contact's last name"""
	user_id: Optional[int]
	"""Contact's user identifier in Telegram. This number may have more than 32 significant bits and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a 64-bit integer or double-precision float type are safe for storing this identifier."""
	vcard: Optional[str]
	"""Additional data about the contact in the form of a vCard"""


class Dice(BaseModel) :
	emoji: str
	"""Emoji on which the dice throw animation is based"""
	value: int
	"""Value of the dice, 1-6 for “🎲”, “🎯” and “🎳” base emoji, 1-5 for “🏀” and “⚽” base emoji, 1-64 for “🎰” base emoji"""


class Game(BaseModel) :
	title: str
	"""Title of the game"""
	description: str
	"""Description of the game"""
	photo: List[PhotoSize]
	"""Photo that will be displayed in the game message in chats."""
	text: Optional[str]
	"""Brief description of the game or high scores included in the game message. Can be automatically edited to include current high scores for the game when the bot calls setGameScore, or manually edited using editMessageText. 0-4096 characters."""
	text_entities: Optional[List[MessageEntity]]
	"""Special entities that appear in text, such as usernames, URLs, bot commands, etc."""
	animation: Optional[Animation]
	"""Animation that will be displayed in the game message in chats. Upload via BotFather"""


class MessageAutoDeleteTimerChanged(BaseModel) :
	message_auto_delete_time: timedelta
	"""New auto-delete time for messages in the chat; in seconds"""


class InlineQuery(BaseModel) :
	id: str
	"""Unique identifier for this query"""
	from_user: User = Field(alias='from')
	"""Sender"""
	query: str
	"""Text of the query (up to 256 characters)"""
	offset: str
	"""Offset of the results to be returned, can be controlled by the bot"""
	chat_type: Optional[ChatType]
	"""Type of the chat from which the inline query was sent. The chat type should be always known for requests sent from official clients and most third-party clients, unless the request was sent from a secret chat"""
	location: Optional[Location]
	"""Sender location, only for bots that request user location"""


class ChosenInlineResult(BaseModel) :
	result_id: str
	"""The unique identifier for the result that was chosen"""
	from_user: User = Field(alias='from')
	"""The user that chose the result"""
	location: Optional[Location]
	"""Sender location, only for bots that require user location"""
	inline_message_id: Optional[str]
	"""Identifier of the sent inline message. Available only if there is an inline keyboard attached to the message. Will be also received in callback queries and can be used to edit the message."""
	query: str
	"""The query that was used to obtain the result"""


class CallbackQuery(BaseModel) :
	id: str
	"""Unique identifier for this query"""
	from_user: User = Field(alias='from')
	"""Sender"""
	message: Optional['Message']
	"""Message with the callback button that originated the query. Note that message content and message date will not be available if the message is too old"""
	inline_message_id: Optional[str]
	"""Identifier of the message sent via the bot in inline mode, that originated the query."""
	chat_instance: str
	"""Global identifier, uniquely corresponding to the chat to which the message with the callback button was sent. Useful for high scores in games."""
	data: Optional[str]
	"""Data associated with the callback button. Be aware that the message originated the query can contain no callback buttons with this data."""
	game_short_name: Optional[str]
	"""Short name of a Game to be returned, serves as the unique identifier for the game"""


class ShippingAddress(BaseModel) :
	country_code: str
	"""Two-letter ISO 3166-1 alpha-2 country code"""
	state: str
	"""State, if applicable"""
	city: str
	"""City"""
	street_line1: str
	"""First line for the address"""
	street_line2: str
	"""Second line for the address"""
	post_code: str
	"""Address post code"""


class ShippingQuery(BaseModel) :
	id: str
	"""Unique query identifier"""
	from_user: User = Field(alias='from')
	"""User who sent the query"""
	invoice_payload: str
	"""Bot specified invoice payload"""
	shipping_address: ShippingAddress
	"""User specified shipping address"""


class OrderInfo(BaseModel) :
	name: Optional[str]
	"""User's name"""
	phone_number: Optional[str]
	"""User's phone number"""
	email: Optional[str]
	"""User's email"""
	shipping_address: Optional[ShippingAddress]
	"""User shipping address"""


class PreCheckoutQuery(BaseModel) :
	id: str
	"""Unique query identifier"""
	from_user: User = Field(alias='from')
	"""User who sent the query"""
	currency: str
	"""Three-letter ISO 4217 currency code"""
	total_amount: int
	"""Total price in the smallest units of the currency (integer, not float/double). For example, for a price of US$ 1.45 pass amount = 145. See the exp parameter in currencies.json, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies)."""
	invoice_payload: str
	"""Bot specified invoice payload"""
	shipping_option_id: Optional[str]
	"""Identifier of the shipping option chosen by the user"""
	order_info: Optional[OrderInfo]
	"""Order information provided by the user"""


class PollOption(BaseModel) :
	text: str
	"""Option text, 1-100 characters"""
	voter_count: int
	"""Number of users that voted for this option"""


class PollType(Enum) :
	"""Poll type, currently can be 'regular' or 'quiz'"""
	regular: str = 'regular'
	quiz: str = 'quiz'


class Poll(BaseModel) :
	id: str
	"""Unique poll identifier"""
	question: str
	"""Poll question, 1-300 characters"""
	options: List[PollOption]
	"""List of poll options"""
	total_voter_count: int
	"""Total number of users that voted in the poll"""
	is_closed: bool
	"""True, if the poll is closed"""
	is_anonymous: bool
	"""True, if the poll is anonymous"""
	type: str
	"""Poll type, currently can be 'regular' or 'quiz'"""
	allows_multiple_answers: bool
	"""True, if the poll allows multiple answers"""
	correct_option_id: Optional[int]
	"""0-based identifier of the correct answer option. Available only for polls in the quiz mode, which are closed, or was sent (not forwarded) by the bot or to the private chat with the bot."""
	explanation: Optional[str]
	"""Text that is shown when a user chooses an incorrect answer or taps on the lamp icon in a quiz-style poll, 0-200 characters"""
	explanation_entities: Optional[List[MessageEntity]]
	"""Special entities like usernames, URLs, bot commands, etc. that appear in the explanation"""
	open_period: Optional[int]
	"""Amount of time in seconds the poll will be active after creation"""
	close_date: Optional[int]
	"""Point in time (Unix timestamp) when the poll will be automatically closed"""


class PollAnswer(BaseModel) :
	poll_id: str
	"""Unique poll identifier"""
	user: User
	"""The user, who changed the answer to the poll"""
	option_ids: List[int]
	"""0-based identifiers of answer options, chosen by the user. May be empty if the user retracted their vote."""


class ChatMemberStatus(Enum) :
	creator: str = 'creator'
	administrator: str = 'administrator'
	member: str = 'member'
	restricted: str = 'restricted'
	left: str = 'left'
	kicked: str = 'kicked'


class ChatMemberOwner(BaseModel) :
	status: ChatMemberStatus = Field(ChatMemberStatus.creator, const=True)
	"""The member's status in the chat, always 'creator'"""
	user: User
	"""Information about the user"""
	is_anonymous: bool
	"""True, if the user's presence in the chat is hidden"""
	custom_title: Optional[str]
	"""Custom title for this user"""


class ChatMemberAdministrator(BaseModel) :
	status: ChatMemberStatus = Field(ChatMemberStatus.administrator, const=True)
	"""The member's status in the chat, always 'administrator'"""
	user: User
	"""Information about the user"""
	can_be_edited: bool
	"""True, if the bot is allowed to edit administrator privileges of that user"""
	is_anonymous: bool
	"""True, if the user's presence in the chat is hidden"""
	can_manage_chat: bool
	"""True, if the administrator can access the chat event log, chat statistics, message statistics in channels, see channel members, see anonymous administrators in supergroups and ignore slow mode. Implied by any other administrator privilege"""
	can_delete_messages: bool
	"""True, if the administrator can delete messages of other users"""
	can_manage_video_chats: bool
	"""True, if the administrator can manage video chats"""
	can_restrict_members: bool
	"""True, if the administrator can restrict, ban or unban chat members"""
	can_promote_members: bool
	"""True, if the administrator can add new administrators with a subset of their own privileges or demote administrators that he has promoted, directly or indirectly (promoted by administrators that were appointed by the user)"""
	can_change_info: bool
	"""True, if the user is allowed to change the chat title, photo and other settings"""
	can_invite_users: bool
	"""True, if the user is allowed to invite new users to the chat"""
	can_post_messages: Optional[bool]
	"""True, if the administrator can post in the channel; channels only"""
	can_edit_messages: Optional[bool]
	"""True, if the administrator can edit messages of other users and can pin messages; channels only"""
	can_pin_messages: Optional[bool]
	"""True, if the user is allowed to pin messages; groups and supergroups only"""
	can_manage_topics: Optional[bool]
	"""True, if the user is allowed to create, rename, close, and reopen forum topics; supergroups only"""
	custom_title: Optional[str]
	"""Custom title for this user"""


class ChatMemberMember(BaseModel) :
	status: ChatMemberStatus = Field(ChatMemberStatus.member, const=True)
	"""The member's status in the chat, always 'member'"""
	user: User
	"""Information about the user"""


class ChatMemberRestricted(BaseModel) :
	status: ChatMemberStatus = Field(ChatMemberStatus.restricted, const=True)
	"""The member's status in the chat, always 'restricted'"""
	user: User
	"""Information about the user"""
	is_member: bool
	"""True, if the user is a member of the chat at the moment of the request"""
	can_change_info: bool
	"""True, if the user is allowed to change the chat title, photo and other settings"""
	can_invite_users: bool
	"""True, if the user is allowed to invite new users to the chat"""
	can_pin_messages: bool
	"""True, if the user is allowed to pin messages"""
	can_manage_topics: bool
	"""True, if the user is allowed to create forum topics"""
	can_send_messages: bool
	"""True, if the user is allowed to send text messages, contacts, locations and venues"""
	can_send_media_messages: bool
	"""True, if the user is allowed to send audios, documents, photos, videos, video notes and voice notes"""
	can_send_polls: bool
	"""True, if the user is allowed to send polls"""
	can_send_other_messages: bool
	"""True, if the user is allowed to send animations, games, stickers and use inline bots"""
	can_add_web_page_previews: bool
	"""True, if the user is allowed to add web page previews to their messages"""
	until_date: datetime
	"""Date when restrictions will be lifted for this user; unix time. If 0, then the user is restricted forever"""


class ChatMemberLeft(BaseModel) :
	status: ChatMemberStatus = Field(ChatMemberStatus.left, const=True)
	"""The member's status in the chat, always 'left'"""
	user: User
	"""Information about the user"""


class ChatMemberBanned(BaseModel) :
	status: ChatMemberStatus = Field(ChatMemberStatus.kicked, const=True)
	"""The member's status in the chat, always 'kicked'"""
	user: User
	"""Information about the user"""
	until_date: datetime
	"""Date when restrictions will be lifted for this user; unix time. If 0, then the user is banned forever"""


ChatMember: type = Union[ChatMemberOwner, ChatMemberAdministrator, ChatMemberMember, ChatMemberRestricted, ChatMemberLeft, ChatMemberBanned]


class ChatInviteLink(BaseModel) :
	invite_link: str
	"""The invite link. If the link was created by another chat administrator, then the second part of the link will be replaced with '…'."""
	creator: User
	"""Creator of the link"""
	creates_join_request: bool
	"""True, if users joining the chat via the link need to be approved by chat administrators"""
	is_primary: bool
	"""True, if the link is primary"""
	is_revoked: bool
	"""True, if the link is revoked"""
	name: Optional[str]
	"""Invite link name"""
	expire_date: Optional[datetime]
	"""Point in time (Unix timestamp) when the link will expire or has been expired"""
	member_limit: Optional[int]
	"""The maximum number of users that can be members of the chat simultaneously after joining the chat via this invite link; 1-99999"""
	pending_join_request_count: Optional[int]
	"""Number of pending join requests created using this link"""


class ChatMemberUpdated(BaseModel) :
	chat: Chat
	"""Chat the user belongs to"""
	from_user: User = Field(alias='from')
	"""Performer of the action, which resulted in the change"""
	date: int
	"""Date the change was done in Unix time"""
	old_chat_member: ChatMember
	"""Previous information about the chat member"""
	new_chat_member: ChatMember
	"""New information about the chat member"""
	invite_link: Optional[ChatInviteLink]
	"""Chat invite link, which was used by the user to join the chat; for joining by invite link events only."""


class ChatJoinRequest(BaseModel) :
	chat: Chat
	"""Chat to which the request was sent"""
	from_user: User = Field(alias='from')
	"""User that sent the join request"""
	date: datetime
	"""Date the request was sent in Unix time"""
	bio: Optional[str]
	"""Bio of the user."""
	invite_link: Optional[ChatInviteLink]
	"""Chat invite link that was used by the user to send the join request"""


class Venue(BaseModel) :
	location: Location
	"""Venue location. Can't be a live location"""
	title: str
	"""Name of the venue"""
	address: str
	"""Address of the venue"""
	foursquare_id: Optional[str]
	"""Foursquare identifier of the venue"""
	foursquare_type: Optional[str]
	"""Foursquare type of the venue. (For example, “arts_entertainment/default”, “arts_entertainment/aquarium” or “food/icecream”.)"""
	google_place_id: Optional[str]
	"""Google Places identifier of the venue"""
	google_place_type: Optional[str]
	"""Google Places type of the venue. (See [supported types](https://developers.google.com/places/web-service/supported_types).)"""


class Invoice(BaseModel) :
	title: str
	"""Product name"""
	description: str
	"""Product description"""
	start_parameter: str
	"""Unique bot deep-linking parameter that can be used to generate this invoice"""
	currency: str
	"""Three-letter ISO 4217 currency code"""
	total_amount: int
	"""Total price in the smallest units of the currency (integer, not float/double). For example, for a price of US$ 1.45 pass amount = 145. See the exp parameter in currencies.json, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies)."""


class SuccessfulPayment(BaseModel) :
	currency: str
	"""Three-letter ISO 4217 currency code"""
	total_amount: int
	"""Total price in the smallest units of the currency (integer, not float/double). For example, for a price of US$ 1.45 pass amount = 145. See the exp parameter in currencies.json, it shows the number of digits past the decimal point for each currency (2 for the majority of currencies)."""
	invoice_payload: str
	"""Bot specified invoice payload"""
	shipping_option_id: Optional[str]
	"""Identifier of the shipping option chosen by the user"""
	order_info: Optional[OrderInfo]
	"""Order information provided by the user"""
	telegram_payment_charge_id: str
	"""Telegram payment identifier"""
	provider_payment_charge_id: str
	"""Provider payment identifier"""


class WriteAccessAllowed(BaseModel) :
	start_date: datetime
	"""Point in time (Unix timestamp) when the video chat is supposed to be started by a chat administrator"""


class EncryptedPassportElementType(Enum) :
	"""Element type. One of “personal_details”, “passport”, “driver_license”, “identity_card”, “internal_passport”, “address”, “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration”, “temporary_registration”, “phone_number”, “email”."""
	personal_details: str = 'personal_details'
	passport: str = 'passport'
	driver_license: str = 'driver_license'
	identity_card: str = 'identity_card'
	internal_passport: str = 'internal_passport'
	address: str = 'address'
	utility_bill: str = 'utility_bill'
	bank_statement: str = 'bank_statement'
	rental_agreement: str = 'rental_agreement'
	passport_registration: str = 'passport_registration'
	temporary_registration: str = 'temporary_registration'
	phone_number: str = 'phone_number'
	email: str = 'email'


class PassportFile(BaseModel) :
	file_id: str
	"""Identifier for this file, which can be used to download or reuse the file"""
	file_unique_id: str
	"""Unique identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file."""
	file_size: int
	"""File size in bytes"""
	file_date: datetime
	"""Unix time when the file was uploaded"""


class EncryptedPassportElement(BaseModel) :
	type: EncryptedPassportElementType
	"""Element type. One of “personal_details”, “passport”, “driver_license”, “identity_card”, “internal_passport”, “address”, “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration”, “temporary_registration”, “phone_number”, “email”."""
	data: Optional[str]
	"""Base64-encoded encrypted Telegram Passport element data provided by the user, available for “personal_details”, “passport”, “driver_license”, “identity_card”, “internal_passport” and “address” types. Can be decrypted and verified using the accompanying EncryptedCredentials."""
	phone_number: Optional[str]
	"""User's verified phone number, available only for “phone_number” type"""
	email: Optional[str]
	"""User's verified email address, available only for “email” type"""
	files: Optional[List[PassportFile]]
	"""Array of encrypted files with documents provided by the user, available for “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration” and “temporary_registration” types. Files can be decrypted and verified using the accompanying EncryptedCredentials."""
	front_side: Optional[PassportFile]
	"""Encrypted file with the front side of the document, provided by the user. Available for “passport”, “driver_license”, “identity_card” and “internal_passport”. The file can be decrypted and verified using the accompanying EncryptedCredentials."""
	reverse_side: Optional[PassportFile]
	"""Encrypted file with the reverse side of the document, provided by the user. Available for “driver_license” and “identity_card”. The file can be decrypted and verified using the accompanying EncryptedCredentials."""
	selfie: Optional[PassportFile]
	"""Encrypted file with the selfie of the user holding a document, provided by the user; available for “passport”, “driver_license”, “identity_card” and “internal_passport”. The file can be decrypted and verified using the accompanying EncryptedCredentials."""
	translation: Optional[List[PassportFile]]
	"""Array of encrypted files with translated versions of documents provided by the user. Available if requested for “passport”, “driver_license”, “identity_card”, “internal_passport”, “utility_bill”, “bank_statement”, “rental_agreement”, “passport_registration” and “temporary_registration” types. Files can be decrypted and verified using the accompanying EncryptedCredentials."""
	hash: str
	"""Base64-encoded element hash for using in PassportElementErrorUnspecified"""


class EncryptedCredentials(BaseModel) :
	data: str
	"""Base64-encoded encrypted JSON-serialized data with unique user's payload, data hashes and secrets required for EncryptedPassportElement decryption and authentication"""
	hash: str
	"""Base64-encoded data hash for data authentication"""
	secret: str
	"""Base64-encoded secret, encrypted with the bot's public RSA key, required for data decryption"""


class PassportData(BaseModel) :
	data: List[EncryptedPassportElement]
	"""Array with information about documents and other Telegram Passport elements that was shared with the bot"""
	credentials: EncryptedCredentials
	"""Encrypted credentials required to decrypt the data"""


class ProximityAlertTriggered(BaseModel) :
	traveler: User
	"""User that triggered the alert"""
	watcher: User
	"""User that set the alert"""
	distance: int
	"""The distance between the users"""


class ForumTopicCreated(BaseModel) :
	name: str
	"""Name of the topic"""
	icon_color: int
	"""Color of the topic icon in RGB format"""
	icon_custom_emoji_id: Optional[str]
	"""Unique identifier of the custom emoji shown as the topic icon"""


class ForumTopicEdited(BaseModel) :
	pass


class ForumTopicClosed(BaseModel) :
	name: Optional[str]
	"""New name of the topic, if it was edited"""
	icon_custom_emoji_id: Optional[str]
	"""New identifier of the custom emoji shown as the topic icon, if it was edited; an empty string if the icon was removed"""


class ForumTopicReopened(BaseModel) :
	pass


class GeneralForumTopicHidden(BaseModel) :
	pass


class GeneralForumTopicUnhidden(BaseModel) :
	pass


class VideoChatScheduled(BaseModel) :
	start_date: datetime
	"""Point in time (Unix timestamp) when the video chat is supposed to be started by a chat administrator"""


class VideoChatStarted(BaseModel) :
	pass


class VideoChatEnded(BaseModel) :
	duration: timedelta
	"""Video chat duration in seconds"""


class VideoChatParticipantsInvited(BaseModel) :
	users: List[User]
	"""New members that were invited to the video chat"""


class WebAppData(BaseModel) :
	data: str
	"""The data. Be aware that a bad client can send arbitrary data in this field."""
	button_text: str
	"""Text of the web_app keyboard button from which the Web App was opened. Be aware that a bad client can send arbitrary data in this field."""


class WebAppInfo(BaseModel) :
	url: HttpUrl
	"""An HTTPS URL of a Web App to be opened with additional data as specified in Initializing Web Apps"""


class LoginUrl(BaseModel) :
	url: HttpUrl
	"""An HTTPS URL to be opened with user authorization data added to the query string when the button is pressed. If the user refuses to provide authorization data, the original URL without information about the user will be opened. The data added is the same as described in Receiving authorization data.
	NOTE: You must always check the hash of the received data to verify the authentication and the integrity of the data as described in Checking authorization."""
	forward_text: Optional[str]
	"""New text of the button in forwarded messages."""
	bot_username: Optional[str]
	"""Username of a bot, which will be used for user authorization. See Setting up a bot for more details. If not specified, the current bot's username will be assumed. The url's domain must be the same as the domain linked with the bot. See Linking your domain to the bot for more details."""
	request_write_access: Optional[bool]
	"""Pass True to request the permission for your bot to send messages to the user."""


class CallbackGame(BaseModel) :
	pass


class InlineKeyboardButton(BaseModel) :
	text: str
	"""Label text on the button"""
	url: Optional[str]
	"""HTTP or tg:// URL to be opened when the button is pressed. Links tg://user?id=<user_id> can be used to mention a user by their ID without using a username, if this is allowed by their privacy settings."""
	callback_data: Optional[str]
	"""Data to be sent in a callback query to the bot when button is pressed, 1-64 bytes"""
	web_app: Optional[WebAppInfo]
	"""Description of the Web App that will be launched when the user presses the button. The Web App will be able to send an arbitrary message on behalf of the user using the method answerWebAppQuery. Available only in private chats between a user and the bot."""
	login_url: Optional[LoginUrl]
	"""An HTTPS URL used to automatically authorize the user. Can be used as a replacement for the Telegram Login Widget."""
	switch_inline_query: Optional[str]
	"""If set, pressing the button will prompt the user to select one of their chats, open that chat and insert the bot's username and the specified inline query in the input field. May be empty, in which case just the bot's username will be inserted.
	NOTE: This offers an easy way for users to start using your bot in inline mode when they are currently in a private chat with it. Especially useful when combined with switch_pm… actions - in this case the user will be automatically returned to the chat they switched from, skipping the chat selection screen."""
	switch_inline_query_current_chat: Optional[str]
	"""If set, pressing the button will insert the bot's username and the specified inline query in the current chat's input field. May be empty, in which case only the bot's username will be inserted.
	This offers a quick way for the user to open your bot in inline mode in the same chat - good for selecting something from multiple options."""
	callback_game: Optional[CallbackGame]
	"""Description of the game that will be launched when the user presses the button.
	NOTE: This type of button must always be the first button in the first row."""
	pay: Optional[bool]
	"""Specify True, to send a Pay button.
	NOTE: This type of button must always be the first button in the first row and can only be used in invoice messages."""


class InlineKeyboardMarkup(BaseModel) :
	inline_keyboard: List[List[InlineKeyboardButton]]
	"""Array of button rows, each represented by an Array of InlineKeyboardButton objects"""


class Message(BaseModel) :
	message_id: int
	"""Unique message identifier inside this chat"""
	message_thread_id: Optional[int]
	"""Unique identifier of a message thread to which the message belongs; for supergroups only"""
	from_user: Optional[User] = Field(alias='from')
	"""Sender of the message; empty for messages sent to channels. For backward compatibility, the field contains a fake sender user in non-channel chats, if the message was sent on behalf of a chat."""
	sender_chat: Optional[Chat]
	"""Sender of the message, sent on behalf of a chat. For example, the channel itself for channel posts, the supergroup itself for messages from anonymous group administrators, the linked channel for messages automatically forwarded to the discussion group. For backward compatibility, the field from contains a fake sender user in non-channel chats, if the message was sent on behalf of a chat."""
	date: datetime
	"""Date the message was sent in Unix time"""
	chat: Chat
	"""Conversation the message belongs to"""
	forward_from: Optional[User]
	"""For forwarded messages, sender of the original message"""
	forward_from_chat: Optional[Chat]
	"""For messages forwarded from channels or from anonymous administrators, information about the original sender chat"""
	forward_from_message_id: Optional[int]
	"""For messages forwarded from channels, identifier of the original message in the channel"""
	forward_signature: Optional[str]
	"""For forwarded messages that were originally sent in channels or by an anonymous chat administrator, signature of the message sender if present"""
	forward_sender_name: Optional[str]
	"""Sender's name for messages forwarded from users who disallow adding a link to their account in forwarded messages"""
	forward_date: Optional[datetime]
	"""For forwarded messages, date the original message was sent in Unix time"""
	is_topic_message: Optional[bool]
	"""True, if the message is sent to a forum topic"""
	is_automatic_forward: Optional[bool]
	"""True, if the message is a channel post that was automatically forwarded to the connected discussion group"""
	reply_to_message: Optional['Message']
	"""For replies, the original message. Note that the Message object in this field will not contain further reply_to_message fields even if it itself is a reply."""
	via_bot: Optional[User]
	"""Bot through which the message was sent"""
	edit_date: Optional[datetime]
	"""Date the message was last edited in Unix time"""
	has_protected_content: Optional[bool]
	"""True, if the message can't be forwarded"""
	media_group_id: Optional[str]
	"""The unique identifier of a media message group this message belongs to"""
	author_signature: Optional[str]
	"""Signature of the post author for messages in channels, or the custom title of an anonymous group administrator"""
	text: Optional[str]
	"""For text messages, the actual UTF-8 text of the message"""
	entities: Optional[List[MessageEntity]] = []
	"""For text messages, special entities like usernames, URLs, bot commands, etc. that appear in the text"""
	animation: Optional[Animation]
	"""Message is an animation, information about the animation. For backward compatibility, when this field is set, the document field will also be set"""
	audio: Optional[Audio]
	"""Message is an audio file, information about the file"""
	document: Optional[Document]
	"""Message is a general file, information about the file"""
	photo: Optional[List[PhotoSize]]
	"""Message is a photo, available sizes of the photo"""
	sticker: Optional[Sticker]
	"""Message is a sticker, information about the sticker"""
	video: Optional[Video]
	"""Message is a video, information about the video"""
	video_note: Optional[VideoNote]
	"""Message is a video note, information about the video message"""
	voice: Optional[Voice]
	"""Message is a voice message, information about the file"""
	caption: Optional[str]
	"""Caption for the animation, audio, document, photo, video or voice"""
	caption_entities: Optional[List[MessageEntity]]
	"""For messages with a caption, special entities like usernames, URLs, bot commands, etc. that appear in the caption"""
	has_media_spoiler: Optional[bool]
	"""True, if the message media is covered by a spoiler animation"""
	contact: Optional[Contact]
	"""Message is a shared contact, information about the contact"""
	dice: Optional[Dice]
	"""Message is a dice with random value"""
	game: Optional[Game]
	"""Message is a game, information about the game. More about games »"""
	poll: Optional[Poll]
	"""Message is a native poll, information about the poll"""
	venue: Optional[Venue]
	"""Message is a venue, information about the venue. For backward compatibility, when this field is set, the location field will also be set"""
	location: Optional[Location]
	"""Message is a shared location, information about the location"""
	new_chat_members: Optional[List[User]]
	"""New members that were added to the group or supergroup and information about them (the bot itself may be one of these members)"""
	left_chat_member: Optional[User]
	"""A member was removed from the group, information about them (this member may be the bot itself)"""
	new_chat_title: Optional[str]
	"""A chat title was changed to this value"""
	new_chat_photo: Optional[List[PhotoSize]]
	"""A chat photo was change to this value"""
	delete_chat_photo: Optional[bool]
	"""Service message: the chat photo was deleted"""
	group_chat_created: Optional[bool]
	"""Service message: the group has been created"""
	supergroup_chat_created: Optional[bool]
	"""Service message: the supergroup has been created. This field can't be received in a message coming through updates, because bot can't be a member of a supergroup when it is created. It can only be found in reply_to_message if someone replies to a very first message in a directly created supergroup."""
	channel_chat_created: Optional[bool]
	"""Service message: the channel has been created. This field can't be received in a message coming through updates, because bot can't be a member of a channel when it is created. It can only be found in reply_to_message if someone replies to a very first message in a channel."""
	message_auto_delete_timer_changed: Optional[MessageAutoDeleteTimerChanged]
	"""Service message: auto-delete timer settings changed in the chat"""
	migrate_to_chat_id: Optional[int]
	"""The group has been migrated to a supergroup with the specified identifier. This number may have more than 32 significant bits and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this identifier."""
	migrate_from_chat_id: Optional[int]
	"""The supergroup has been migrated from a group with the specified identifier. This number may have more than 32 significant bits and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed 64-bit integer or double-precision float type are safe for storing this identifier."""
	pinned_message: Optional['Message']
	"""Specified message was pinned. Note that the Message object in this field will not contain further reply_to_message fields even if it is itself a reply."""
	invoice: Optional[Invoice]
	"""Message is an invoice for a payment, information about the invoice. More about payments »"""
	successful_payment: Optional[SuccessfulPayment]
	"""Message is a service message about a successful payment, information about the payment. More about payments »"""
	connected_website: Optional[str]
	"""The domain name of the website on which the user has logged in. More about Telegram Login »"""
	write_access_allowed: Optional[WriteAccessAllowed]
	"""Service message: the user allowed the bot added to the attachment menu to write messages"""
	passport_data: Optional[PassportData]
	"""Telegram Passport data"""
	proximity_alert_triggered: Optional[ProximityAlertTriggered]
	"""Service message. A user in the chat triggered another user's proximity alert while sharing Live Location."""
	forum_topic_created: Optional[ForumTopicCreated]
	"""Service message: forum topic created"""
	forum_topic_edited: Optional[ForumTopicEdited]
	"""Service message: forum topic edited"""
	forum_topic_closed: Optional[ForumTopicClosed]
	"""Service message: forum topic closed"""
	forum_topic_reopened: Optional[ForumTopicReopened]
	"""Service message: forum topic reopened"""
	general_forum_topic_hidden: Optional[GeneralForumTopicHidden]
	"""Service message: the 'General' forum topic hidden"""
	general_forum_topic_unhidden: Optional[GeneralForumTopicUnhidden]
	"""Service message: the 'General' forum topic unhidden"""
	video_chat_scheduled: Optional[VideoChatScheduled]
	"""Service message: video chat scheduled"""
	video_chat_started: Optional[VideoChatStarted]
	"""Service message: video chat started"""
	video_chat_ended: Optional[VideoChatEnded]
	"""Service message: video chat ended"""
	video_chat_participants_invited: Optional[VideoChatParticipantsInvited]
	"""Service message: new participants invited to a video chat"""
	web_app_data: Optional[WebAppData]
	"""Service message: data sent by a Web App"""
	reply_markup: Optional[InlineKeyboardMarkup]
	"""Inline keyboard attached to the message. login_url buttons are represented as ordinary url buttons."""


class Update(BaseModel) :
	update_id: int
	"""The update's unique identifier. Update identifiers start from a certain positive number and increase sequentially. This ID becomes especially handy if you're using webhooks, since it allows you to ignore repeated updates or to restore the correct update sequence, should they get out of order. If there are no new updates for at least a week, then identifier of the next update will be chosen randomly instead of sequentially."""
	message: Optional[Message]
	"""New incoming message of any kind - text, photo, sticker, etc."""
	edited_message: Optional[Message]
	"""New version of a message that is known to the bot and was edited"""
	channel_post: Optional[Message]
	"""New incoming channel post of any kind - text, photo, sticker, etc."""
	edited_channel_post: Optional[Message]
	"""New version of a channel post that is known to the bot and was edited"""
	inline_query: Optional[InlineQuery]
	"""New incoming inline query"""
	chosen_inline_result: Optional[ChosenInlineResult]
	"""The result of an inline query that was chosen by a user and sent to their chat partner. Please see our documentation on the feedback collecting for details on how to enable these updates for your bot."""
	callback_query: Optional[CallbackQuery]
	"""New incoming callback query"""
	shipping_query: Optional[ShippingQuery]
	"""New incoming shipping query. Only for invoices with flexible price"""
	pre_checkout_query: Optional[PreCheckoutQuery]
	"""New incoming pre-checkout query. Contains full information about checkout"""
	poll: Optional[Poll]
	"""New poll state. Bots receive only updates about stopped polls and polls, which are sent by the bot"""
	poll_answer: Optional[PollAnswer]
	"""A user changed their answer in a non-anonymous poll. Bots receive new votes only in polls that were sent by the bot itself."""
	my_chat_member: Optional[ChatMemberUpdated]
	"""The bot's chat member status was updated in a chat. For private chats, this update is received only when the bot is blocked or unblocked by the user."""
	chat_member: Optional[ChatMemberUpdated]
	"""A chat member's status was updated in a chat. The bot must be an administrator in the chat and must explicitly specify 'chat_member' in the list of allowed_updates to receive these updates."""
	chat_join_request: Optional[ChatJoinRequest]
	"""A request to join the chat has been sent. The bot must have the can_invite_users administrator right in the chat to receive these updates."""


class Updates(BaseModel) :
	ok: bool
	description: Optional[str]
	result: List[Update]
