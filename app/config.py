from pathlib import Path

#user agent to identify where the request is coming from(not a bot)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

#Base DIR for all files
BASE_DIR = Path(__file__).resolve().parents[1]

DESTINATIONS = [
    {
        "name": "Diani",
        "slug": "diani",
        "url": "https://magicalkenya.com/place-to-go/diani/",
    },
    {
        "name": "Maasai Mara",
        "slug": "maasai-mara",
        "url": "https://magicalkenya.com/place-to-go/maasai-mara/",
    },
    {
        "name": "Chale Island Reef",
        "slug": "chale-island-reef",
        "url": "https://magicalkenya.com/place-to-go/chale-island-reef/",
    },
    {
        "name": "Nanyuki",
        "slug": "nanyuki",
        "url": "https://magicalkenya.com/place-to-go/nanyuki/",
    },
    {
        "name": "Mount Longonot",
        "slug": "mount-longonot",
        "url": "https://magicalkenya.com/place-to-go/mount-longonot/",
    },
    {
        "name": "Ol Pejeta Conservancy",
        "slug": "ol-pejeta-conservancy",
        "url": "https://magicalkenya.com/place-to-go/ol-pejeta-conservancy/",
    },
    {
        "name": "Turkana",
        "slug": "turkana",
        "url": "https://magicalkenya.com/place-to-go/turkana/",
    },
    {
        "name": "Rift Valley",
        "slug": "Rift-Valley",
        "url": "https://magicalkenya.com/place-to-go/the-great-rift-valley/",
    },
    {
        "name": "Kilifi",
        "slug": "Kilifi-Coast",
        "url": "https://magicalkenya.com/place-to-go/kilifi-coast/",
    },
]

KWS_DESTINATIONS = [
    {
        "name": "Aberdare National Park",
        "slug": "aberdare-national-park",
        "url": "https://kws.go.ke/park/aberdare-national-park/",
    },
    {
        "name": "Amboseli National Park",
        "slug": "amboseli-national-park",
        "url": "https://kws.go.ke/park/amboseli-national-park/",
    },
    {
        "name": "Central Island National Park",
        "slug": "central-island-national-park",
        "url": "https://kws.go.ke/park/central-island-national-park/",
    },
    {
        "name": "Chyulu Hills National Park",
        "slug": "chyulu-hills-national-park",
        "url": "https://kws.go.ke/park/chyulu-hills-national-park/",
    },
    {
        "name": "Diani Chale National Reserve",
        "slug": "diani-chale-national-reserve",
        "url": "https://kws.go.ke/park/diani-chale-national-reserve/",
    },
    {
        "name": "Hell's Gate National Park",
        "slug": "hells-gate-national-park",
        "url": "https://kws.go.ke/park/hells-gate-national-park/",
    },
    {
        "name": "Kakamega Forest National Reserve",
        "slug": "kakamega-forest-national-reserve",
        "url": "https://kws.go.ke/park/kakamega-forest-national-reserve/",
    },
    {
        "name": "Kisite Mpunguti Marine National Park",
        "slug": "kisite-mpunguti-marine-national-park",
        "url": "https://kws.go.ke/park/kisite-mpunguti-marine-national-park/",
    },
    {
        "name": "Kisumu Impala Sanctuary",
        "slug": "kisumu-impala-sanctuary",
        "url": "https://kws.go.ke/park/kisumu-impala-sanctuary/",
    },
    {
        "name": "Kiunga Marine National Reserve",
        "slug": "kiunga-marine-national-reserve",
        "url": "https://kws.go.ke/park/kiunga-marine-national-reserve/",
    },
    {
        "name": "Kora National Park",
        "slug": "kora-national-park",
        "url": "https://kws.go.ke/park/kora-national-park/",
    },
    {
        "name": "Lake Elementaita Wildlife Sanctuary",
        "slug": "lake-elementaita-wildlife-sanctuary",
        "url": "https://kws.go.ke/park/lake-elementaita-wildlife-sanctuary/",
    },
    {
        "name": "Lake Nakuru National Park",
        "slug": "lake-nakuru-national-park",
        "url": "https://kws.go.ke/park/lake-nakuru-national-park/",
    },
    {
        "name": "Malindi Marine National Park & Reserve",
        "slug": "malindi-marine-national-park-reserve",
        "url": "https://kws.go.ke/park/malindi-marine-national-park-reserve/",
    },
    {
        "name": "Malka Mari National Park",
        "slug": "malka-mari-national-park",
        "url": "https://kws.go.ke/park/malka-mari-national-park/",
    },
    {
        "name": "Marsabit National Park",
        "slug": "marsabit-national-park",
        "url": "https://kws.go.ke/park/marsabit-national-park/",
    },
    {
        "name": "Meru National Park",
        "slug": "meru-national-park",
        "url": "https://kws.go.ke/park/meru-national-park/",
    },
    {
        "name": "Mombasa Marine National Park & Reserve",
        "slug": "mombasa-marine-national-park-reserve",
        "url": "https://kws.go.ke/park/mombasa-marine-national-park-reserve/",
    },
    {
        "name": "Mt. Elgon National Park",
        "slug": "mt-elgon-national-park",
        "url": "https://kws.go.ke/park/mt-elgon-national-park/",
    },
    {
        "name": "Mt. Kenya National Park",
        "slug": "mt-kenya-national-park",
        "url": "https://kws.go.ke/park/mt-kenya-national-park/",
    },
    {
        "name": "Mt. Longonot National Park",
        "slug": "mt-longonot-national-park",
        "url": "https://kws.go.ke/park/mt-longonot-national-park/",
    },
    {
        "name": "Mwea National Reserve",
        "slug": "mwea-national-reserve",
        "url": "https://kws.go.ke/park/mwea-national-reserve/",
    },
    {
        "name": "Nairobi Animal Orphanage",
        "slug": "nairobi-animal-orphanage",
        "url": "https://kws.go.ke/park/nairobi-animal-orphanage/",
    },
    {
        "name": "Nairobi National Park",
        "slug": "nairobi-national-park",
        "url": "https://kws.go.ke/park/nairobi-national-park/",
    },
    {
        "name": "Nairobi Safari Walk",
        "slug": "nairobi-safari-walk",
        "url": "https://kws.go.ke/park/nairobi-safari-walk/",
    },
    {
        "name": "Ndere Island National Park",
        "slug": "ndere-island-national-park",
        "url": "https://kws.go.ke/park/ndere-island-national-park/",
    },
    {
        "name": "Oldonyo Sabuk National Park",
        "slug": "oldonyo-sabuk-national-park",
        "url": "https://kws.go.ke/park/oldonyo-sabuk-national-park/",
    },
    {
        "name": "Ruma National Park",
        "slug": "ruma-national-park",
        "url": "https://kws.go.ke/park/ruma-national-park/",
    },
    {
        "name": "Saiwa Swamp National Park",
        "slug": "saiwa-swamp-national-park",
        "url": "https://kws.go.ke/park/saiwa-swamp-national-park/",
    },
    {
        "name": "Shimba Hills National Reserve",
        "slug": "shimba-hills-national-reserve",
        "url": "https://kws.go.ke/park/shimba-hills-national-reserve/",
    },
    {
        "name": "Sibiloi National Park",
        "slug": "sibiloi-national-park",
        "url": "https://kws.go.ke/park/sibiloi-national-park/",
    },
    {
        "name": "South Island National Park",
        "slug": "south-island-national-park",
        "url": "https://kws.go.ke/park/south-island-national-park/",
    },
    {
        "name": "Tsavo East National Park",
        "slug": "tsavo-east-national-park",
        "url": "https://kws.go.ke/park/tsavo-east-national-park/",
    },
    {
        "name": "Tsavo West National Park",
        "slug": "tsavo-west-national-park",
        "url": "https://kws.go.ke/park/tsavo-west-national-park/",
    },
    {
        "name": "Watamu Marine National Park & Reserve",
        "slug": "watamu-marine-national-park-reserve",
        "url": "https://kws.go.ke/park/watamu-marine-national-park-reserve/",
    },
]