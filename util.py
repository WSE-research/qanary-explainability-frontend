import random

def include_css(st, filenames):
    content = ""
    for filename in filenames:
        with open(filename) as f:
            content += f.read()
    st.markdown(f"<style>{content}</style>", unsafe_allow_html=True)

def get_random_element(elements):
    return elements[random.randint(0, len(elements) - 1)]

feedback_messages = [
    "Hey, thanks a bunch for your help!",
    "You rock! Thanks for your feedback.",
    "You're the best; thanks for your help!",
    "Much appreciated. Thanks!",
    "You're a lifesaver; thank you!",
    "I can't thank you enough for your support.",
    "Big thanks for all your help!",
    "I owe you one, thanks!",
    "You're a \u2605; thanks for your help!",
    "Thanks a million for your support!",
    "Thanks for being such a great supporter!",
    "Your help meant the world to me. Here's a hug-filled thank you!",
    "Super grateful for your help.",
    "Thanks a ton for your support!",
    "Couldn't have done it without you. Thanks!",
    "You're awesome; thanks for everything!",
    "Thanks for being so supportive!",
    "I really appreciate it; you're so kind!",
    "Your help was right on time. Thanks!",
    "I appreciate your help more than you'll ever know.",
    "Kudos to you, and thanks a million!",
    "Thank you for brightening my day!",
    "You've been incredible! Thanks a ton.",
    "Thank you. Let's go for a drink at the next opportunity!"
]

feedback_icons = [
    "🙏",
    "🤗",
    "👍",
    "👏",
    "👌"
]