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
        "id": "people-style",
        "name": "People & Style",
        "description": "Portraits by look: headshots, outfits, dresses, details, people in scenery, pure scenery.",
        "categories": [
            _c("headshots", "Headshots & portraits", "🧑", "a close-up headshot portrait of a person",
               "a studio portrait of a face", "a black and white portrait photograph of a person"),
            _c("selfies", "Selfies", "🤳", "a selfie taken at arm's length with a phone",
               "a person taking a selfie", "a mirror selfie with a phone"),
            _c("outfits", "Full-body outfits", "🧍", "a full-body photo of a person showing their outfit",
               "a person posing in a stylish outfit on the street", "street style fashion photo of a whole outfit"),
            _c("dresses", "Dresses & formal wear", "👗", "a woman wearing an elegant dress",
               "a person in a suit or formal wear", "an evening gown at a gala event"),
            _c("casual", "Casual & streetwear", "👟", "a person in jeans and sneakers",
               "a casual streetwear outfit with a hoodie or t-shirt", "an everyday casual look"),
            _c("details", "Outfit details", "👜", "a close-up of shoes", "a handbag or fashion accessories",
               "a close-up of jewelry or a watch"),
            _c("runway", "Runway & editorial", "📸", "a fashion runway show with a model on the catwalk",
               "an editorial fashion photo shoot", "a model posing for a fashion magazine"),
            _c("people-scenery", "People in scenery", "🏞️", "a person standing in a wide landscape",
               "a traveler posing in front of a scenic view", "a person on a beach or mountain"),
            _c("scenery", "Scenery", "🌄", "a landscape with no people", "a city skyline or street with no people",
               "mountains, sea and nature scenery"),
            _c("groups", "Groups & friends", "👯", "a group of friends posing together", "a crowd of people",
               "people together at a party or event"),
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

# ---------------------------------------------------------------- more presets
def _v(id: str, name: str, emoji: str, *prompts: str) -> dict:
    return {**_c(id, name, emoji, *prompts), "media": "video"}


PRESETS += [
    {
        "id": "shoots",
        "name": "Photoshoot themes",
        "description": "For photographers: sort a mixed archive by the theme of each shoot.",
        "categories": [
            _c("wedding", "Wedding", "💍", "a bride in a white wedding dress", "a wedding ceremony", "a bride and groom posing together"),
            _c("engagement", "Engagement & couples", "💑", "a romantic couple photoshoot", "a couple holding hands outdoors", "an engagement ring proposal"),
            _c("halloween", "Halloween", "🎃", "a halloween costume", "pumpkins and spooky halloween decorations", "a person in scary halloween makeup"),
            _c("christmas", "Christmas", "🎄", "a christmas tree with lights", "people in christmas sweaters", "christmas presents and decorations"),
            _c("moto", "Moto", "🏍️", "a person posing with a motorcycle", "a motorbike on a road", "a biker in a leather jacket and helmet"),
            _c("cars", "Cars", "🚗", "a person posing with a sports car", "a classic car photoshoot", "a car on a scenic road"),
            _c("pool-beach", "Pool & beach", "🏖️", "a swimsuit photoshoot by the pool", "a model on a sandy beach by the sea", "a person swimming in a pool"),
            _c("studio", "Studio", "💡", "a studio portrait on a plain seamless backdrop", "a model in a photo studio with softbox lighting", "a studio photoshoot on a white background"),
            _c("urban", "Urban & street", "🏙️", "a model posing in a city street", "a photoshoot with graffiti walls", "an urban rooftop photoshoot"),
            _c("nature-shoot", "Nature & forest", "🌲", "a portrait photoshoot in a forest", "a person in a flower field", "a photoshoot in the mountains"),
            _c("maternity", "Maternity", "🤰", "a pregnant woman maternity photoshoot", "a pregnant belly with hands", "a maternity portrait in a flowing dress"),
            _c("newborn", "Newborn & baby", "👶", "a newborn baby sleeping", "a baby photoshoot with props", "parents holding a newborn"),
            _c("family", "Family", "👨‍👩‍👧", "a family portrait with children", "parents and kids playing outdoors", "a multi-generation family photo"),
            _c("corporate", "Corporate & headshots", "💼", "a professional corporate headshot", "business people in an office", "a person in a suit on a neutral background"),
            _c("events", "Events & parties", "🎉", "people dancing at a party", "a birthday party with cake", "a concert or event stage with lights"),
            _c("fashion", "Fashion editorial", "👠", "a high fashion editorial photo", "a model posing in designer clothes", "a fashion lookbook photo"),
            _c("boudoir", "Boudoir", "🕯️", "an intimate boudoir photo in a bedroom", "a woman in lingerie posing", "a sensual portrait with soft window light"),
            _c("sport-shoot", "Sport & fitness", "🏋️", "an athlete training", "a fitness photoshoot in a gym", "a person running or doing yoga"),
            _c("product", "Product & food", "📦", "a product photo on a clean background", "a styled food photo", "a flat lay of products"),
            _c("real-estate", "Real estate & interiors", "🏠", "a bright living room interior", "a modern kitchen interior", "the exterior of a house"),
        ],
    },
    {
        "id": "wedding-day",
        "name": "Wedding day",
        "description": "One wedding, sorted into the chapters of the day.",
        "categories": [
            _c("getting-ready", "Getting ready", "💄", "a bride getting her makeup and hair done", "a groom putting on his suit and tie", "a wedding dress hanging by a window"),
            _c("details", "Details & rings", "💍", "a close-up of wedding rings", "wedding shoes, invitation and perfume flat lay", "a bridal bouquet close-up"),
            _c("ceremony", "Ceremony", "⛪", "a wedding ceremony at the altar", "a couple exchanging vows", "guests seated at a wedding ceremony"),
            _c("couple", "Couple portraits", "💑", "a bride and groom posing together", "a romantic portrait of newlyweds", "a couple kissing in a beautiful landscape"),
            _c("family-groups", "Family & groups", "👨‍👩‍👧‍👦", "a large group photo of wedding guests", "a family portrait with the bride and groom", "bridesmaids and groomsmen posing"),
            _c("venue", "Venue & decor", "🌸", "a decorated wedding reception hall", "wedding table decorations with flowers", "an empty wedding venue"),
            _c("party", "Party & first dance", "💃", "a couple's first dance", "guests dancing at a wedding party", "a wedding party at night with lights"),
            _c("cake-food", "Cake & food", "🎂", "a wedding cake", "cutting the wedding cake", "a wedding dinner buffet"),
            _v("wedding-video", "Video clips", "🎬", "a wedding video", "a couple at a wedding"),
        ],
    },
    {
        "id": "instagram",
        "name": "Instagram creator",
        "description": "A content creator's camera roll: looks, places, people, video by setting.",
        "categories": [
            _c("two-girls", "Two friends", "👭", "two women posing together", "two girls taking a photo together", "a pair of female friends side by side"),
            _c("couple", "Couple", "💑", "a romantic couple, a man and a woman together", "a couple hugging", "a couple holding hands"),
            _c("fashion-outdoor", "Fashion outdoor", "🌤️", "a fashion photo of a woman posing outdoors in a stylish outfit", "street style outfit photographed outside", "a model posing in a park or city street"),
            _c("fashion-indoor", "Fashion indoor", "🛋️", "a fashion photo of a woman posing indoors in a stylish outfit", "an outfit photo inside an apartment or hotel room", "a model posing indoors near a window"),
            _c("photoshoot-outfits", "Photoshoot outfits", "📸", "a professional photoshoot of a model in an outfit", "a studio fashion photoshoot with lighting", "a lookbook photo"),
            _c("details", "Details", "💅", "a close-up of clothing, shoes or accessories", "a close-up of jewelry, nails or makeup", "a detail shot of a handbag"),
            _c("selfies", "Selfies", "🤳", "a selfie taken with a phone at arm's length", "a mirror selfie", "a close-up selfie of a face"),
            _c("sport", "Sport", "🏋️", "a woman working out in a gym", "fitness training or yoga", "a person in sportswear exercising"),
            _c("sea-pool", "Sea & pool", "🌊", "a woman at the beach by the sea", "a person by a swimming pool", "a swimsuit photo near water"),
            _c("moto", "Moto", "🏍️", "a woman posing on a motorbike", "a motorcycle", "a biker with a helmet"),
            _c("mountain", "Mountain", "🏔️", "mountains landscape", "a woman hiking in the mountains", "snowy mountain peaks"),
            _c("man", "Man", "🧔", "a photo of a man alone", "a male portrait", "a man posing for a photo"),
            _v("video-indoor", "Video indoor", "🎥", "a video filmed indoors in a room", "an indoor scene inside a house or studio"),
            _v("video-outdoor", "Video outdoor", "🎞️", "a video filmed outdoors", "an outdoor scene with sky, street or nature"),
        ],
    },
    {
        "id": "boudoir",
        "name": "Boudoir & glamour",
        "description": "Boudoir, lingerie and glamour sessions sorted by setup, wardrobe and mood.",
        "categories": [
            _c("lingerie-studio", "Lingerie · studio", "🖤", "a model in lingerie in a photo studio with a plain backdrop",
               "a lingerie photoshoot with studio lighting", "a woman in a lace bra and panties posing in a studio"),
            _c("lingerie-bedroom", "Lingerie · bedroom", "🛏️", "a woman in lingerie in a bedroom", "a lingerie photo next to a window in a hotel room",
               "a boudoir photo in a bedroom with soft light"),
            _c("on-the-bed", "On the bed", "🌙", "a woman lying on a bed in lingerie", "a sensual pose on white bed sheets", "a model kneeling on a bed"),
            _c("corset", "Corset & bodysuit", "🎀", "a woman wearing a corset", "a model in a bodysuit", "a black corset with garters"),
            _c("stockings", "Stockings & heels", "👠", "legs in stockings and high heels", "a woman wearing stockings and a garter belt",
               "a close-up of legs in sheer stockings"),
            _c("robe-shirt", "Robe & oversized shirt", "👘", "a woman in a silk robe", "a woman wearing only an oversized white shirt", "a satin robe boudoir photo"),
            _c("implied", "Silhouette & implied", "🌫️", "a silhouette of a woman against a window", "an implied nude covered with a sheet",
               "a woman's back with soft shadows"),
            _c("bw", "Black & white", "⚫", "a black and white boudoir portrait", "a monochrome glamour photo"),
            _c("details", "Details", "💋", "a close-up of lace lingerie details", "red lips and jewelry close-up", "hands and fabric detail"),
            _c("glamour", "Glamour portrait", "✨", "a glamour portrait with makeup and styled hair", "a pin-up style photo", "a sensual close-up portrait"),
            _c("outdoor", "Outdoor & swimwear", "🌊", "a woman in a bikini at the beach", "a boudoir photo outdoors in nature", "a swimwear photo by the pool"),
            _c("runway", "Runway & show", "💃", "a lingerie fashion show runway", "a model on a catwalk in lingerie and wings"),
        ],
    },
    {
        "id": "family",
        "name": "Family & kids",
        "description": "Home life: kids, family moments, holidays, school, pets.",
        "categories": [
            _c("babies", "Babies", "👶", "a baby", "a newborn baby sleeping", "a toddler crawling"),
            _c("kids", "Kids", "🧒", "a child playing", "kids at a playground", "a child smiling at the camera"),
            _c("family", "Family moments", "👨‍👩‍👧", "a family together at home", "parents with their children", "grandparents with grandchildren"),
            _c("birthdays", "Birthdays", "🎂", "a birthday cake with candles", "a kids birthday party with balloons", "people singing happy birthday"),
            _c("holidays", "Holidays", "🎄", "christmas at home", "an easter egg hunt", "a family holiday dinner"),
            _c("school", "School & sports", "🏫", "a child at school", "a kids sports game", "a school performance on stage"),
            _c("vacation", "Vacation", "🏖️", "a family on the beach", "kids in a swimming pool", "a family trip sightseeing"),
            _c("pets", "Pets", "🐾", "a dog", "a cat", "a child with a pet"),
            _c("art", "Kids' art & docs", "🖍️", "a child's drawing", "a school certificate or report", "handmade crafts by children"),
            SCREENSHOTS,
        ],
    },
    {
        "id": "events",
        "name": "Events & parties",
        "description": "Conferences, concerts, parties and celebrations.",
        "categories": [
            _c("stage", "Stage & speakers", "🎤", "a speaker on stage at a conference", "a presenter with slides", "a panel discussion"),
            _c("concert", "Concerts & DJs", "🎸", "a band performing on stage with lights", "a DJ at a club", "a crowd at a concert"),
            _c("audience", "Audience & crowd", "👥", "an audience seated in a hall", "a crowd of people", "people clapping"),
            _c("networking", "Networking", "🤝", "people talking in small groups at an event", "people shaking hands", "guests holding drinks and chatting"),
            _c("party", "Party & dance", "💃", "people dancing at a party", "a nightclub dance floor", "friends celebrating with drinks"),
            _c("venue", "Venue & decor", "🏛️", "an empty event venue", "decorated tables at an event", "a stage setup before an event"),
            _c("catering", "Food & drinks", "🥂", "a catering buffet", "cocktails at a bar", "plated food at an event"),
            _c("group", "Group photos", "📸", "a posed group photo", "a team photo", "friends posing together"),
            _c("branding", "Signs & branding", "🪧", "an event banner or logo", "a branded backdrop", "signage at an event"),
        ],
    },
    {
        "id": "real-estate",
        "name": "Real estate",
        "description": "Listing photos by room.",
        "categories": [
            _c("exterior", "Exterior", "🏡", "the exterior facade of a house", "a building from the street", "a front yard and entrance"),
            _c("living", "Living room", "🛋️", "a living room with a sofa", "a lounge area with a TV", "a bright open-plan living space"),
            _c("kitchen", "Kitchen", "🍳", "a kitchen with cabinets and appliances", "a kitchen island", "a dining area next to a kitchen"),
            _c("bedroom", "Bedroom", "🛏️", "a bedroom with a bed", "a master bedroom", "a kids bedroom"),
            _c("bathroom", "Bathroom", "🛁", "a bathroom with a shower", "a bathtub and sink", "a toilet and vanity"),
            _c("office", "Office & study", "💻", "a home office with a desk", "a study room with bookshelves"),
            _c("outdoor", "Garden & terrace", "🌿", "a garden", "a balcony or terrace", "a swimming pool in a backyard"),
            _c("view", "Views", "🌆", "a view from a window", "a city view from a balcony"),
            _c("plans", "Floor plans", "📐", "a floor plan drawing", "an architectural plan"),
        ],
    },
    {
        "id": "nature",
        "name": "Nature & wildlife",
        "description": "Landscapes and animals.",
        "categories": [
            _c("mountains", "Mountains", "🏔️", "mountain peaks", "a mountain valley", "snowy mountains"),
            _c("sea", "Sea & coast", "🌊", "the sea and waves", "a rocky coastline", "a beach at sunset"),
            _c("forest", "Forest", "🌲", "a dense forest", "a forest path", "tall trees"),
            _c("lakes", "Lakes & rivers", "🏞️", "a calm lake", "a river through a valley", "a waterfall"),
            _c("sky", "Sky & sunsets", "🌅", "a dramatic sunset", "clouds in the sky", "the night sky with stars"),
            _c("flowers", "Flowers & plants", "🌸", "a close-up of flowers", "a field of wildflowers", "a plant leaf macro"),
            _c("birds", "Birds", "🐦", "a bird perched on a branch", "a bird in flight"),
            _c("mammals", "Wild animals", "🦊", "a wild animal in nature", "a deer in a forest", "a fox or a bear"),
            _c("insects", "Insects & macro", "🦋", "a butterfly on a flower", "an insect macro photo"),
            _c("snow", "Snow & winter", "❄️", "a snowy landscape", "winter trees covered in snow"),
        ],
    },
    {
        "id": "food-product",
        "name": "Food & product",
        "description": "For e-commerce and food photographers.",
        "categories": [
            _c("packshot", "Packshots", "📦", "a product on a plain white background", "an isolated product photo", "a packshot for an online shop"),
            _c("lifestyle-product", "Lifestyle product", "🛍️", "a product being used by a person", "a styled product scene", "a product on a table at home"),
            _c("flatlay", "Flat lays", "🗂️", "a top-down flat lay of objects", "products arranged neatly from above"),
            _c("cosmetics", "Cosmetics", "🧴", "cosmetic bottles and creams", "makeup products", "skincare products"),
            _c("dishes", "Plated dishes", "🍽️", "a plated restaurant dish", "a gourmet meal on a plate"),
            _c("drinks", "Drinks", "🍹", "a cocktail", "a cup of coffee", "a glass of wine"),
            _c("desserts", "Desserts & baking", "🍰", "a dessert", "cakes and pastries", "bread and baked goods"),
            _c("ingredients", "Ingredients", "🥕", "raw ingredients on a table", "fresh vegetables and fruit"),
            _c("bts", "Behind the scenes", "🎬", "a photo studio setup with lights", "a food stylist at work"),
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

# ------------------------------------------------------------ auto-discovery facets
# Each facet is a bank of (label, CLIP prompt). Auto mode clusters on the chosen facets and names a group
# by what distinguishes it from the rest of the folder (z-scored prompt similarity).
FACETS: dict[str, list[tuple[str, str]]] = {
    "subject": [
        ("Portraits", "a portrait photo of one person"), ("Couple", "a romantic couple together"),
        ("Group", "a group of people posing together"), ("Kids", "children playing"),
        ("Pets", "a dog or a cat"), ("Food", "a plate of food"), ("Cars & moto", "a car or a motorcycle"),
        ("Landscape", "a landscape with no people"), ("Architecture", "buildings and architecture"),
        ("Products", "a product photo"), ("Screenshots", "a screenshot of a phone screen"),
        ("Text", "an image with written text"), ("Flowers", "flowers close up"), ("Animals", "wild animals"),
    ],
    "scene": [
        ("Studio", "a photo studio with a plain seamless backdrop"), ("Indoors", "inside a house or apartment"),
        ("Bedroom", "a bedroom with a bed"), ("Mountains", "mountains and rocky peaks"),
        ("Forest", "a forest with trees"), ("Meadow", "a green meadow with grass"),
        ("Beach & sea", "a beach by the sea"), ("Pool", "a swimming pool"), ("City", "a city street with buildings"),
        ("Night", "a scene at night"), ("Snow", "snow and winter"), ("Venue", "a decorated event hall"),
        ("Car / garage", "next to a car or motorcycle"), ("Desert", "a desert with sand dunes"),
    ],
    "framing": [
        ("Close-up", "a tight close-up of a face"), ("Half-body", "a waist-up portrait"),
        ("Full-body", "a full-body photo of a standing person"), ("Wide", "a wide shot with a small person in a big landscape"),
        ("Details", "a close-up detail of hands, shoes, jewelry or fabric"), ("From behind", "a person seen from behind"),
        ("Sitting", "a person sitting"), ("Lying down", "a person lying down"), ("Walking", "a person walking"),
        ("Dancing", "people dancing or twirling"), ("Overhead", "a photo taken from above"),
    ],
    "lighting": [
        ("Golden hour", "warm golden hour sunlight"), ("Daylight", "bright even daylight"),
        ("Overcast", "soft overcast light and grey sky"), ("Window light", "soft window light indoors"),
        ("High-key", "a bright high-key studio photo with white background"), ("Low-key", "a dark low-key photo with deep shadows"),
        ("Neon", "neon and colored lights"), ("Black & white", "a black and white photo"),
        ("Backlit", "backlit silhouette against the light"), ("Flash", "direct flash photography at night"),
    ],
    "outfit": [
        ("Wedding dress", "a white wedding dress"), ("Evening gown", "an elegant evening gown"),
        ("Suit", "a man in a suit"), ("Casual", "casual jeans and t-shirt"), ("Streetwear", "streetwear with sneakers and hoodie"),
        ("Sportswear", "sportswear and leggings"), ("Swimwear", "a bikini or swimsuit"), ("Lingerie", "lingerie"),
        ("Costume", "a halloween costume"), ("Leather", "a black leather jacket"), ("Winter coat", "a winter coat and scarf"),
        ("Corset", "a corset or bodysuit"), ("Stockings", "stockings and garters"), ("Robe", "a silk robe or oversized shirt"),
        ("Summer dress", "a light summer dress"),
    ],
}

FOCUS_FACETS: dict[str, list[str]] = {
    "auto": ["subject", "scene", "framing", "lighting"],
    "scene": ["scene"],
    "framing": ["framing"],
    "outfit": ["outfit"],
    "lighting": ["lighting"],
    "subject": ["subject"],
}

FOCUS_HINT = {
    "auto": "whatever best separates the groups",
    "scene": "the scene / location",
    "framing": "framing and pose (close-up, full-body, sitting, details…)",
    "outfit": "the outfit / clothing",
    "lighting": "the lighting and mood",
    "subject": "the main subject",
}

# What kind of collection is this? (shown in the UI and given to the AI as context)
THEMES: list[tuple[str, str]] = [
    ("Wedding", "a wedding with a bride and groom"), ("Trash the dress", "a bride in a wedding dress posing in wild nature or mountains"),
    ("Engagement", "an engagement photoshoot of a couple"), ("Studio fashion", "a fashion photoshoot in a studio"),
    ("Boudoir", "an intimate boudoir photoshoot"), ("Lingerie studio", "a lingerie photoshoot in a studio"),
    ("Glamour", "glamour and pin-up photography"), ("Halloween", "halloween costumes and decorations"),
    ("Moto", "a photoshoot with motorcycles"), ("Pool & beach", "a swimwear photoshoot by the pool or beach"),
    ("Travel", "travel photos of places and landmarks"), ("Family", "family photos with children"),
    ("Sport & fitness", "sport and fitness photos"), ("Christmas", "christmas celebration"),
    ("Product", "product photography"), ("Real estate", "interior and real estate photos"),
    ("Street fashion", "street style fashion outfits in the city"), ("Everyday", "everyday phone photos and selfies"),
    ("Event", "an event or party"), ("Nature", "nature and landscape photography"),
]


# ------------------------------------------------------------ recipes (what the UI recommends)
# One click sets everything up. The UI translates titles/descriptions by id.
RECIPES: list[dict] = [
    {"id": "camera-roll", "emoji": "📱", "strategy": "preset", "set_id": "lifestyle", "options": {}},
    {"id": "photoshoot", "emoji": "📸", "strategy": "cull",
     "options": {"quality": {"bursts": True, "picks_percent": 20, "smiles": True}}},
    {"id": "wedding", "emoji": "💍", "strategy": "preset", "set_id": "wedding-day",
     "options": {"quality": {"enabled": True, "action": "tag"}}},
    {"id": "boudoir", "emoji": "🖤", "strategy": "preset", "set_id": "boudoir",
     "options": {"quality": {"enabled": True, "action": "tag"}}},
    {"id": "portraits", "emoji": "👗", "strategy": "preset", "set_id": "people-style", "options": {}},
    {"id": "people", "emoji": "🧑‍🤝‍🧑", "strategy": "people", "options": {}},
    {"id": "travel", "emoji": "✈️", "strategy": "preset", "set_id": "travel", "options": {}},
    {"id": "documents", "emoji": "🧾", "strategy": "preset", "set_id": "documents", "options": {"ocr": True}},
    {"id": "discover", "emoji": "✨", "strategy": "auto", "options": {"focus": "auto"}},
    {"id": "by-date", "emoji": "📅", "strategy": "date", "options": {}},
]
RECIPES_BY_ID = {r["id"]: r for r in RECIPES}

THEME_TO_RECIPE = {
    "Wedding": "wedding", "Trash the dress": "wedding", "Engagement": "wedding",
    "Boudoir": "boudoir", "Lingerie studio": "boudoir", "Glamour": "boudoir",
    "Studio fashion": "portraits", "Street fashion": "portraits",
    "Travel": "travel", "Nature": "travel",
    "Everyday": "camera-roll", "Family": "camera-roll", "Event": "camera-roll", "Christmas": "camera-roll",
    "Halloween": "camera-roll", "Moto": "camera-roll", "Pool & beach": "camera-roll", "Sport & fitness": "camera-roll",
    "Product": "discover", "Real estate": "discover",
}
SHOOT_THEMES = {"Wedding", "Trash the dress", "Engagement", "Boudoir", "Lingerie studio", "Glamour", "Studio fashion"}
