# API Response Schemas & Field Mappings

This document captures the actual response objects from each Tier 1 API and defines the exact field mapping to our canonical `Listing` model. The implementing agent should use this as the source of truth when writing `_normalize()` methods in `vehicle_search.py`.

---

## 1. MarketCheck

**Endpoint:** `GET https://api.marketcheck.com/v2/search/car/active`

**Response wrapper:**
```json
{
  "num_found": 12345,
  "listings": [ ...Listing objects... ]
}
```

**Listing object (TypeScript interface from their docs):**

```typescript
interface Listing {
  id: string;
  vin: string;
  heading?: string;
  price?: number;
  miles?: number;
  msrp?: number;
  vdp_url?: string;
  exterior_color?: string;
  interior_color?: string;
  base_ext_color?: string;
  base_int_color?: string;
  dom: number;               // days on market (lifetime)
  dom_180: number;
  dom_active: number;
  seller_type: string;        // "dealer" | "fsbo" | "auction"
  inventory_type: string;     // "new" | "used"
  is_certified?: number;      // 1 if CPO
  stock_no?: string;
  last_seen_at: number;       // unix seconds
  source: string;             // website domain
  media?: {
    photo_links?: string[];
    photo_links_cached?: string[];
  };
  dealer?: {
    id: number;
    name: string;
    dealer_type?: string;
    city?: string;
    state?: string;
    zip?: string;
    phone?: string;
  };
  build?: {
    year: number;
    make: string;
    model?: string;
    trim?: string;
    body_type?: string;
    vehicle_type?: string;
    transmission?: string;
    drivetrain?: string;       // "FWD" | "RWD" | "4WD" | "AWD"
    fuel_type?: string;        // "Unleaded" | "Diesel" | "Electric" | "Premium Unleaded" | etc.
    engine?: string;           // "2.0L I4" | "Electric Motor" | etc.
    engine_size?: number;
    cylinders?: number;
    doors?: number;
    highway_mpg?: number;
    city_mpg?: number;
    powertrain_type?: string;  // "Combustion" | "BEV" | "HEV" | "MHEV" | "PHEV"
  };
}
```

### MarketCheck → Listing mapping

| Listing field | MarketCheck path | Transform |
|---|---|---|
| `source` | (literal) | `Source.MARKETCHECK` |
| `source_id` | `id` | str |
| `vin` | `vin` | str |
| `make` | `build.make` | str |
| `model` | `build.model` | str |
| `year` | `build.year` | int |
| `trim` | `build.trim` | str or None |
| `drivetrain` | `build.drivetrain` | Map: `"FWD"`→`Drivetrain.FWD`, `"RWD"`→`RWD`, `"4WD"`→`FOUR_WD`, `"AWD"`→`AWD` |
| `fuel_type` | `build.fuel_type` + `build.powertrain_type` | Map: `powertrain_type == "BEV"` → `FuelType.ELECTRIC`, `"PHEV"` → `PLUG_IN_HYBRID`, `"HEV"/"MHEV"` → `HYBRID`, `fuel_type` contains `"Diesel"` → `DIESEL`, else `GASOLINE` |
| `body_style` | `build.body_type` | str.lower() or None |
| `transmission` | `build.transmission` | str or None |
| `engine` | `build.engine` | str or None |
| `exterior_color` | `exterior_color` or `base_ext_color` | Prefer `base_ext_color` (standardized) |
| `interior_color` | `interior_color` or `base_int_color` | Prefer `base_int_color` (standardized) |
| `battery_capacity_kwh` | — | Not available directly. Null. |
| `range_miles` | — | Not available directly. Null. |
| `price` | `price` | float or None |
| `mileage` | `miles` | int or None |
| `condition` | `inventory_type` + `is_certified` | `"new"` → `Condition.NEW`, `is_certified == 1` → `CERTIFIED`, else `USED` |
| `seller_type` | `seller_type` | `"dealer"` → `SellerType.DEALER`, `"fsbo"` → `PRIVATE`, `"auction"` → `AUCTION` |
| `days_on_market` | `dom_active` | int |
| `city` | `dealer.city` | str or None |
| `state` | `dealer.state` | str or None |
| `zip` | `dealer.zip` | str or None |
| `url` | `vdp_url` | str or None |
| `image_url` | `media.photo_links[0]` or `media.photo_links_cached[0]` | First photo URL |
| `dealer_name` | `dealer.name` | str or None |
| `raw` | (entire listing dict) | dict |

---

## 2. Auto.dev

**Endpoint:** `GET https://api.auto.dev/listings`

**Response wrapper:**
```json
{
  "data": [ ...listing objects... ]
}
```

**Listing object (from their docs):**

```json
{
  "@id": "https://api.auto.dev/listings/10ARJYBS7RC154562",
  "vin": "10ARJYBS7RC154562",
  "location": [-77.0334, 40.2476],
  "createdAt": "2025-09-14 14:04:06",
  "vehicle": {
    "vin": "10ARJYBS7RC154562",
    "squishVin": "10ARJYBSRC",
    "year": 2024,
    "make": "Jeep",
    "model": "Grand Cherokee",
    "trim": "4xe",
    "drivetrain": "4WD",
    "engine": "Plug-In Hybrid",
    "fuel": "Plug-In Hybrid",
    "transmission": "Automatic",
    "confidence": 0.005,
    "doors": 4,
    "seats": 5
  },
  "wholesaleListing": {
    "auction": "OVE",
    "miles": 89868
  },
  "retailListing": {
    "vdp": "http://...",
    "price": 119000,
    "used": true,
    "cpo": false,
    "carfaxUrl": "https://www.carfax.com/...",
    "dealer": "Indy Cars & Trucks",
    "city": "Indianapolis",
    "state": "IN",
    "zip": "17050",
    "primaryImage": "https://retail.photos.vin/...",
    "photoCount": 1
  },
  "history": {
    "accidents": false,
    "ownerCount": 7
  }
}
```

### Auto.dev → Listing mapping

| Listing field | Auto.dev path | Transform |
|---|---|---|
| `source` | (literal) | `Source.AUTODEV` |
| `source_id` | `vin` | str (VIN is the listing key) |
| `vin` | `vin` | str |
| `make` | `vehicle.make` | str |
| `model` | `vehicle.model` | str |
| `year` | `vehicle.year` | int |
| `trim` | `vehicle.trim` | str or None |
| `drivetrain` | `vehicle.drivetrain` | Map: `"4WD"`→`FOUR_WD`, `"AWD"`→`AWD`, `"FWD"`→`FWD`, `"RWD"`→`RWD` |
| `fuel_type` | `vehicle.fuel` | Map: `"Electric"`→`ELECTRIC`, `"Plug-In Hybrid"`→`PLUG_IN_HYBRID`, `"Hybrid"`→`HYBRID`, contains `"Diesel"`→`DIESEL`, else `GASOLINE` |
| `body_style` | — | Not in listing response. Null. |
| `transmission` | `vehicle.transmission` | str or None |
| `engine` | `vehicle.engine` | str or None |
| `exterior_color` | — | Not in listing search results. Null. |
| `interior_color` | — | Not in listing search results. Null. |
| `battery_capacity_kwh` | — | Not available. Null. |
| `range_miles` | — | Not available. Null. |
| `price` | `retailListing.price` | float or None. **If 0, treat as None** (their API returns 0 for missing). |
| `mileage` | `retailListing.miles` or `wholesaleListing.miles` | int or None. Prefer retailListing. |
| `condition` | `retailListing.used` + `retailListing.cpo` | `used == false` → `Condition.NEW`, `cpo == true` → `CERTIFIED`, else `USED` |
| `seller_type` | presence of `wholesaleListing` | If `wholesaleListing` with `auction` → `AUCTION`, else `DEALER` |
| `days_on_market` | — | Not available. Null. |
| `city` | `retailListing.city` | str or None |
| `state` | `retailListing.state` | str or None |
| `zip` | `retailListing.zip` | str or None |
| `url` | `retailListing.vdp` | str or None |
| `image_url` | `retailListing.primaryImage` | str or None |
| `dealer_name` | `retailListing.dealer` | str or None |
| `raw` | (entire listing dict) | dict |

---

## 3. Driv.ly (listings.vin)

**Endpoint:** `GET https://listings.vin/`

**Response wrapper:**
```json
{
  "total": 2122738,
  "links": { "self": "...", "next": "...", "last": "..." },
  "data": [ ...listing objects... ],
  "facets": { ... }
}
```

**Listing object (from their docs):**

```json
{
  "vin": "1GYKPFRS4RZ701252",
  "url": "http://listings.vin/1GYKPFRS4RZ701252",
  "vehicle": {
    "vin": "1GYKPFRS4RZ701252",
    "squishVin": "1GYKPFRSRZ",
    "year": 2024,
    "make": "Cadillac",
    "model": "XT6",
    "trim": "Premium Luxury",
    "series": "Premium Luxury 4dr SUV AWD (3.6L 6cyl 9A)",
    "bodyStyle": "SUV",
    "type": ["Crossover", "Luxury", "SUV"],
    "style": "4dr SUV",
    "drivetrain": "4WD",
    "engine": "3.6L 6Cyl gasoline",
    "cylinders": 6,
    "fuel": "Regular Unleaded",
    "transmission": "Automatic",
    "confidence": 0.995,
    "interiorColor": "Black",
    "exteriorColor": "White",
    "baseMsrp": 56995,
    "baseInvoice": 54145,
    "doors": 4,
    "seats": 7
  },
  "retailListing": {
    "vdp": "/cadillac-xt6#vin=1GYKPFRS4RZ701252",
    "price": 58911,
    "miles": 7494,
    "used": true,
    "cpo": false,
    "carfaxUrl": "https://...",
    "dealer": "Ken Batchelor Cadillac",
    "city": "San Antonio",
    "state": "TX",
    "primaryImage": "https://retail.photos.vin/...",
    "photoCount": 30,
    "margin": null
  },
  "wholesaleListing": {
    "vdp": "https://members.manheim.com/...",
    "buyNowPrice": 20800,
    "miles": 80559,
    "mmr": 16750,
    "seller": "...",
    "auction": "...",
    "city": "...",
    "state": "..."
  },
  "autocheck": {
    "numberOfAccidents": 0,
    "ownerCount": 2,
    "score": 87
  },
  "score": 3
}
```

### Driv.ly → Listing mapping

| Listing field | Driv.ly path | Transform |
|---|---|---|
| `source` | (literal) | `Source.DRIVLY` |
| `source_id` | `vin` | str (VIN is the listing key) |
| `vin` | `vin` | str |
| `make` | `vehicle.make` | str |
| `model` | `vehicle.model` | str |
| `year` | `vehicle.year` | int |
| `trim` | `vehicle.trim` | str or None |
| `drivetrain` | `vehicle.drivetrain` | Map: `"4WD"`→`FOUR_WD`, `"AWD"`→`AWD`, `"FWD"`→`FWD`, `"RWD"`→`RWD`, `"4x4"`→`FOUR_WD` |
| `fuel_type` | `vehicle.fuel` + `vehicle.engine` | Map: `fuel` contains `"Electric"` or engine contains `"Electric"` → `ELECTRIC`, `"Plug-In Hybrid"` → `PLUG_IN_HYBRID`, `"Hybrid"` → `HYBRID`, `"Diesel"` → `DIESEL`, else `GASOLINE` |
| `body_style` | `vehicle.bodyStyle` | str.lower() or None |
| `transmission` | `vehicle.transmission` | str or None |
| `engine` | `vehicle.engine` | str or None |
| `exterior_color` | `vehicle.exteriorColor` | str or None |
| `interior_color` | `vehicle.interiorColor` | str or None |
| `battery_capacity_kwh` | — | Not available. Null. |
| `range_miles` | — | Not available. Null. |
| `price` | `retailListing.price` | float or None |
| `mileage` | `retailListing.miles` | int or None |
| `condition` | `retailListing.used` + `retailListing.cpo` | `used == false` → `NEW`, `cpo == true` → `CERTIFIED`, else `USED` |
| `seller_type` | presence of `wholesaleListing` | If `wholesaleListing.auction` → `AUCTION`, else `DEALER` |
| `days_on_market` | — | Not available. Null. |
| `city` | `retailListing.city` | str or None |
| `state` | `retailListing.state` | str or None |
| `zip` | — | Not in response. Null. |
| `url` | `url` | str (the `listings.vin` URL) |
| `image_url` | `retailListing.primaryImage` | str or None |
| `dealer_name` | `retailListing.dealer` | str or None |
| `raw` | (entire listing dict) | dict |

**Note:** Driv.ly and Auto.dev share the same underlying data platform. Their response shapes are nearly identical. The `vehicle` and `retailListing` structures match. The key differences: Driv.ly includes `bodyStyle`, `exteriorColor`, `interiorColor`, `baseMsrp`, `autocheck`, and `wholesaleListing` more reliably.

---

## 4. Carapis (CarGurus)

**Endpoint:** `POST https://api.carapis.com/v1/parsers/cargurus/search`

**Response wrapper:**
```json
{
  "success": true,
  "data": {
    "listings": [ ...listing objects... ],
    "total_count": 1200,
    "search_metadata": {
      "query": "...",
      "market": "us",
      "pagination": { "limit": 20, "offset": 0, "has_more": true }
    }
  }
}
```

**Listing object (from their docs):**

```json
{
  "id": "123456789",
  "title": "Ford F-150 XLT",
  "price": {
    "amount": 42000,
    "currency": "USD",
    "formatted": "$42,000",
    "negotiable": false
  },
  "deal_rating": {
    "score": 9.2,
    "label": "Great Deal",
    "explanation": "Priced $2,500 below market average"
  },
  "specifications": {
    "year": 2020,
    "mileage": 35000,
    "fuel_type": "Gasoline",
    "transmission": "Automatic",
    "engine_size": "3.5L V6",
    "power": "400 hp",
    "torque": "500 lb-ft",
    "drivetrain": "4WD",
    "mpg_city": 20,
    "mpg_highway": 26,
    "vin": "1FTEW1EG0JFA12345"
  },
  "location": {
    "city": "New York",
    "state": "NY",
    "country": "United States",
    "postal_code": "10001",
    "coordinates": { "lat": 40.7128, "lng": -74.006 }
  },
  "seller": {
    "name": "NYC Ford Dealership",
    "type": "dealer",
    "rating": 4.7,
    "reviews_count": 150,
    "certified": true,
    "contact": { "phone": "...", "email": "..." }
  },
  "features": ["Navigation System", "Leather Seats", ...],
  "images": ["https://example.com/image1.jpg", ...],
  "url": "https://www.cargurus.com/...",
  "extracted_at": "2024-01-15T10:30:00Z",
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### Carapis → Listing mapping

| Listing field | Carapis path | Transform |
|---|---|---|
| `source` | (literal) | `Source.CARAPIS` |
| `source_id` | `id` | str |
| `vin` | `specifications.vin` | str or None (not always present in search results) |
| `make` | parse from `title` | Split title to extract make. E.g. `"Ford F-150 XLT"` → `"Ford"`. |
| `model` | parse from `title` | Split title to extract model. E.g. `"Ford F-150 XLT"` → `"F-150"`. |
| `year` | `specifications.year` | int |
| `trim` | parse from `title` | Remainder after make+model. E.g. `"Ford F-150 XLT"` → `"XLT"`. |
| `drivetrain` | `specifications.drivetrain` | Map: `"4WD"`→`FOUR_WD`, `"AWD"`→`AWD`, `"FWD"`→`FWD`, `"RWD"`→`RWD` |
| `fuel_type` | `specifications.fuel_type` | Map: `"Electric"`→`ELECTRIC`, `"Plug-In Hybrid"` or `"plug_in_hybrid"`→`PLUG_IN_HYBRID`, `"Hybrid"`→`HYBRID`, `"Diesel"`→`DIESEL`, `"Gasoline"`→`GASOLINE` |
| `body_style` | — | Not in response. Null. |
| `transmission` | `specifications.transmission` | str or None |
| `engine` | `specifications.engine_size` | str or None (e.g. `"3.5L V6"`) |
| `exterior_color` | — | Not in search results. Null. |
| `interior_color` | — | Not in search results. Null. |
| `battery_capacity_kwh` | — | Not available. Null. |
| `range_miles` | — | Not available. Null. |
| `price` | `price.amount` | float or None |
| `mileage` | `specifications.mileage` | int or None |
| `condition` | `seller.certified` | If `certified == true` → `CERTIFIED`. No new/used flag available — default to `USED`. |
| `seller_type` | `seller.type` | `"dealer"` → `DEALER`, `"private"` → `PRIVATE`, else `UNKNOWN` |
| `days_on_market` | — | Not directly available. Could derive from `extracted_at` vs `last_updated` but unreliable. Null. |
| `city` | `location.city` | str or None |
| `state` | `location.state` | str or None |
| `zip` | `location.postal_code` | str or None |
| `url` | `url` | str or None |
| `image_url` | `images[0]` | First image URL or None |
| `dealer_name` | `seller.name` | str or None |
| `raw` | (entire listing dict) | dict |

**Note:** Carapis embeds make/model in the `title` field rather than as separate fields. The normalizer needs a title parser. Since we're always searching by make+model, we can pass the search params through to populate these fields reliably rather than relying on title parsing.

---

## Field coverage matrix

Shows which fields are available from each source. Critical for understanding where the model will have missing data.

| Listing field | MarketCheck | Auto.dev | Driv.ly | Carapis |
|---|---|---|---|---|
| `vin` | yes | yes | yes | sometimes |
| `make` | yes | yes | yes | from title |
| `model` | yes | yes | yes | from title |
| `year` | yes | yes | yes | yes |
| `trim` | yes | yes | yes | from title |
| `drivetrain` | yes | yes | yes | yes |
| `fuel_type` | yes | yes | yes | yes |
| `body_style` | yes | no | yes | no |
| `transmission` | yes | yes | yes | yes |
| `engine` | yes | yes | yes | partial |
| `exterior_color` | yes | no | yes | no |
| `interior_color` | yes | no | yes | no |
| `battery_capacity_kwh` | no | no | no | no |
| `range_miles` | no | no | no | no |
| `price` | yes | yes (0=missing) | yes | yes |
| `mileage` | yes | yes | yes | yes |
| `condition` | yes | yes | yes | partial |
| `seller_type` | yes | inferred | inferred | yes |
| `days_on_market` | yes | no | no | no |
| `city` | yes | yes | yes | yes |
| `state` | yes | yes | yes | yes |
| `zip` | yes | yes | no | yes |
| `url` | yes | yes | yes | yes |
| `image_url` | yes | yes | yes | yes |
| `dealer_name` | yes | yes | yes | yes |

**Key takeaways for the ML model:**
- `battery_capacity_kwh` and `range_miles` are not available from any listing API — must be enriched from EPA data or NHTSA VIN decode (future enhancement)
- `days_on_market` is only reliably available from MarketCheck
- `exterior_color` and `interior_color` are missing from Auto.dev and Carapis
- MarketCheck has the richest field coverage across the board
