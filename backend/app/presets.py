"""Built-in category presets and the auto-naming vocabulary (REQ-CAT-1, REQ-CAT-5)."""
from __future__ import annotations


def _c(id: str, name: str, emoji: str, *prompts: str) -> dict:
    return {"id": id, "name": name, "emoji": emoji, "prompts": list(prompts)}


SCREENSHOTS = _c(
    "screenshots", "Screenshots", "📱",
    "a screenshot of a phone app", "a screenshot of a website", "a screenshot of a chat conversation",
    "a screenshot of a social media feed",
)
TEXT = _c(
    "text-captions", "Text & captions", "💬",
    "an image with large text or a quote", "a meme with a caption", "a poster with typography",
    "a graphic with written words on a plain background",
)

PRESETS: list[dict] = [
    {
        "id": "lifestyle",
        "name": "Lifestyle",
        "description": "The everyday camera roll: selfies, outfits, food, travel, spaces.",
        "categories": [
            _c("selfies", "Selfies & portraits", "🤳", "a selfie of a person", "a close-up portrait of a person's face",
               "a person talking to the camera", "a smiling person looking at the camera"),
            _c("outfits", "Outfits & fashion", "👗", "a full-body photo of a person showing their outfit",
               "an outfit of the day mirror photo", "clothes, shoes and accessories", "a fashion photo"),
            _c("food", "Food & cafés", "🥐", "a photo of food on a plate", "a cup of coffee in a café",
               "a restaurant table with dishes", "desserts and pastries"),
            _c("travel", "Travel & vibe", "✈️", "a travel photo of a famous destination", "a view from an airplane window",
               "a vacation photo by the sea", "a street in a foreign old town"),
            _c("nature", "Nature", "🌿", "a landscape of mountains and forest", "flowers and plants close up",
               "a sunset over the sea", "trees, lakes and nature"),
            _c("aesthetic-spaces", "Aesthetic spaces", "🕯️", "a beautiful interior design of a room",
               "minimalist aesthetic home decor", "a cozy bedroom with soft light", "an elegant architectural interior"),
            _c("sport", "Sport & wellness", "🧘", "a person working out in a gym", "yoga or pilates class",
               "running or cycling outdoors", "fitness and sports equipment"),
            _c("music-hobby", "Music & hobby", "🎸", "a person playing a musical instrument",
               "a concert stage with lights", "a hobby like painting, crafting or reading", "vinyl records and headphones"),
            _c("work", "Work from home", "💻", "a laptop on a desk", "a home office workspace",
               "a computer screen with documents", "a video call meeting"),
            _c("pets", "Pets", "🐾", "a photo of a dog", "a photo of a cat", "a cute pet animal"),
            TEXT,
            SCREENSHOTS,
        ],
    },
    {
        "id": "travel",
        "name": "Travel",
        "description": "Sort a trip by kind of place and moment.",
        "categories": [
            _c("beaches", "Beaches & sea", "🏖️", "a sandy beach with the sea", "people swimming in the ocean", "a boat on clear water"),
            _c("mountains", "Mountains & hiking", "🏔️", "mountains and a hiking trail", "a snowy mountain peak", "a person hiking"),
            _c("cities", "Cities & streets", "🏙️", "a busy city street", "a city skyline", "a narrow old town street"),
            _c("landmarks", "Landmarks & monuments", "🗿", "a famous landmark", "a historic monument", "a cathedral or temple"),
            _c("stays", "Hotels & stays", "🛏️", "a hotel room", "a hotel pool", "an apartment rental interior"),
            _c("food", "Food & markets", "🍜", "local street food", "a food market stall", "a restaurant meal"),
            _c("transport", "Transport & airports", "🚆", "an airport terminal", "a train or bus journey", "a view from an airplane window"),
            _c("nightlife", "Night life", "🌃", "a city at night with lights", "a bar or party at night", "fireworks"),
            _c("people", "People & friends", "👯", "a group of friends posing", "a selfie on vacation", "people smiling together"),
            _c("screenshots", "Screenshots & tickets", "🎟️", "a screenshot of a phone app", "a boarding pass or ticket",
               "a map screenshot", "a booking confirmation"),
        ],
    },
    {
        "id": "creator",
        "name": "Creator",
        "description": "For content creators: talking heads, try-ons, products, b-roll.",
        "categories": [
            _c("talking", "Talking to camera", "🎙️", "a person talking to the camera", "a vlogger speaking in a room", "a close-up of a person speaking"),
            _c("outfits", "Outfits & try-ons", "👠", "a mirror outfit try-on", "a full-body fashion photo", "clothes laid out flat"),
            _c("products", "Product shots", "🛍️", "a product photo on a clean background", "a cosmetic product close-up", "an unboxing of a product"),
            _c("broll", "B-roll scenery", "🎞️", "a cinematic landscape shot", "a scenic city view", "aesthetic slow-motion details"),
            _c("bts", "Behind the scenes", "🎬", "a camera setup with ring light", "a film set behind the scenes", "a messy workspace with gear"),
            TEXT,
            _c("memes", "Memes", "😂", "a funny meme image", "a reaction image with text", "a cartoon joke"),
            SCREENSHOTS,
        ],
    },
    {
        "id": "documents",
        "name": "Documents",
        "description": "Receipts, IDs, notes and slides hiding in your camera roll.",
        "categories": [
            _c("receipts", "Receipts & invoices", "🧾", "a photo of a paper receipt", "an invoice document", "a bill with prices"),
            _c("ids", "IDs & cards", "🪪", "an identity card or passport", "a bank card", "a business card"),
            _c("notes", "Notes & whiteboards", "📝", "handwritten notes on paper", "a whiteboard with writing", "a notebook page"),
            _c("slides", "Slides & charts", "📊", "a presentation slide", "a chart or graph", "a projector screen in a meeting"),
            SCREENSHOTS,
            _c("photos", "Photos (other)", "🖼️", "a regular photo of people or places", "a landscape photo", "a photo of objects"),
        ],
    },
]

PRESETS_BY_ID = {p["id"]: p for p in PRESETS}

# Vocabulary for naming auto-discovered clusters without an LLM (label, emoji).
VOCABULARY: list[tuple[str, str]] = [
    ("Selfies", "🤳"), ("Portraits", "🧑"), ("Group Photos", "👯"), ("Couples", "💑"), ("Babies & Kids", "👶"),
    ("Family", "👨‍👩‍👧"), ("Weddings", "💍"), ("Parties", "🎉"), ("Birthdays", "🎂"), ("Concerts", "🎤"),
    ("Outfits", "👗"), ("Shoes", "👟"), ("Makeup & Beauty", "💄"), ("Nails", "💅"), ("Hair", "💇"),
    ("Jewelry", "💍"), ("Bags", "👜"), ("Mirror Selfies", "🪞"), ("Food", "🍽️"), ("Coffee", "☕"),
    ("Desserts", "🍰"), ("Drinks & Cocktails", "🍹"), ("Cooking", "🍳"), ("Restaurants", "🍝"), ("Breakfast", "🥞"),
    ("Fruit", "🍓"), ("Pizza", "🍕"), ("Sushi", "🍣"), ("Beach", "🏖️"), ("Sea & Ocean", "🌊"),
    ("Pools", "🏊"), ("Mountains", "🏔️"), ("Snow & Skiing", "⛷️"), ("Forest", "🌲"), ("Flowers", "🌸"),
    ("Plants", "🪴"), ("Sunsets", "🌅"), ("Sky & Clouds", "☁️"), ("Night Sky", "🌌"), ("Lakes & Rivers", "🏞️"),
    ("Desert", "🏜️"), ("Gardens & Parks", "🌳"), ("City Streets", "🏙️"), ("Skylines", "🌆"), ("Architecture", "🏛️"),
    ("Churches & Temples", "⛪"), ("Museums & Art", "🖼️"), ("Landmarks", "🗼"), ("Old Towns", "🏘️"), ("Night City", "🌃"),
    ("Airports & Planes", "✈️"), ("Airplane Windows", "🛫"), ("Trains", "🚆"), ("Cars", "🚗"), ("Road Trips", "🛣️"),
    ("Boats", "⛵"), ("Bikes", "🚲"), ("Hotels", "🏨"), ("Interiors", "🛋️"), ("Bedrooms", "🛏️"),
    ("Kitchens", "🍽️"), ("Home Decor", "🕯️"), ("Cafés", "☕"), ("Shops", "🛍️"), ("Markets", "🧺"),
    ("Gym & Fitness", "🏋️"), ("Yoga", "🧘"), ("Running", "🏃"), ("Football", "⚽"), ("Tennis", "🎾"),
    ("Swimming", "🏊"), ("Hiking", "🥾"), ("Cycling", "🚴"), ("Dance", "💃"), ("Music", "🎸"),
    ("Pianos", "🎹"), ("Books & Reading", "📚"), ("Painting & Art", "🎨"), ("Crafts", "🧶"), ("Gaming", "🎮"),
    ("Photography Gear", "📷"), ("Laptops & Desks", "💻"), ("Office", "🏢"), ("Meetings", "👥"), ("Whiteboards", "📝"),
    ("Documents", "📄"), ("Receipts", "🧾"), ("Handwritten Notes", "✍️"), ("Slides", "📊"), ("Charts", "📈"),
    ("Screenshots", "📱"), ("Chat Screenshots", "💬"), ("Social Media", "📲"), ("Memes", "😂"), ("Quotes", "🗨️"),
    ("Text Graphics", "🔤"), ("Maps", "🗺️"), ("Tickets", "🎟️"), ("Products", "📦"), ("Cosmetics", "🧴"),
    ("Dogs", "🐶"), ("Cats", "🐱"), ("Birds", "🐦"), ("Horses", "🐴"), ("Wildlife", "🦊"),
    ("Aquarium & Fish", "🐠"), ("Christmas", "🎄"), ("Halloween", "🎃"), ("Fireworks", "🎆"), ("Candles", "🕯️"),
    ("Cartoons & Illustrations", "🖍️"), ("Logos & Icons", "🔷"), ("Patterns & Textures", "🧵"), ("Black & White", "⚫"),
    ("Videos of People Talking", "🎙️"),
]
