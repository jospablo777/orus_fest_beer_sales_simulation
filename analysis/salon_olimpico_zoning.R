# Zoning of Salón Olímpico Pantitlán (Mexico City) on source map data.
#
# Venue outline: the OpenStreetMap building polygon that contains `venue_point`. If OSM
# has no such building, the outline is digitized once over Esri World Imagery and saved
# to `outline_path`; later runs read that file.
# Zones: rectangles in meters in the building's local frame (long and short axes of the
# minimum rotated rectangle of the outline), clipped to the outline.
#
# Outputs: CSV with dimensions, areas and occupancy; zones as GeoJSON; leaflet map.
#
# Packages: sf, leaflet, htmlwidgets, osmdata; mapedit only when digitizing.

library(sf)
library(leaflet)

# Parameters -------------------------------------------------------------------

venue_point     <- c(lon = -99.06916, lat = 19.41226)  # any point inside the hall
search_radius_m <- 80
outline_path    <- "salon_outline.geojson"
use_osm         <- TRUE
crs_m           <- 32614                               # WGS 84 / UTM 14N
min_outline_m2  <- 300                                 # smaller outlines are rejected

m2_per_person_standing <- 0.46  # NFPA 101 12.1.7, assembly areas of up to 930 m²
m2_per_person_tables   <- 1.39  # NFPA 101, less concentrated use without fixed seating

# Zone layout in the building's local frame, in meters:
#   u: distance from the stage wall (south) toward the bar wall (north), 0..L
#   v: distance from the west wall toward the east wall, 0..W
# Depths and widths come from the first estimate made on the annotated screenshot.
# Tables sit in the west corner in front of the bar, as in the annotated screenshot.
layout_zones <- function(L, W) {
  data.frame(
    zone  = c("stage", "bar", "tables", "vendors", "vendors"),
    label = c("Stage", "Alcohol and food", "Tables",
              "Vendors (west)", "Vendors (east)"),
    u0 = c(0, L - 9, L - 18, 11,   12.5),
    u1 = c(9, L,     L - 9,  33,   L - 9),
    v0 = c(0, 0,     0,      0,    W - 5),
    v1 = c(W, W,     9,      5,    W)
  )
}

zone_colors <- c(venue = "#FA2332", bar = "#28B9D7", tables = "#FFB91E",
                 stage = "#8C3CFF", vendors = "#6ED746")

# Venue outline ----------------------------------------------------------------

satellite_basemap <- function() {
  leaflet(options = leafletOptions(maxZoom = 22)) |>
    addProviderTiles(providers$Esri.WorldImagery,
                     options = providerTileOptions(maxNativeZoom = 19, maxZoom = 22))
}

outline_from_osm <- function(pt) {
  if (!use_osm || !requireNamespace("osmdata", quietly = TRUE)) return(NULL)
  bbox <- st_bbox(st_transform(st_buffer(st_transform(pt, crs_m), search_radius_m), 4326))
  res <- tryCatch(
    osmdata::osmdata_sf(osmdata::add_osm_feature(osmdata::opq(bbox), key = "building")),
    error = function(e) {
      message("Overpass query failed: ", conditionMessage(e))
      NULL
    }
  )
  if (is.null(res)) return(NULL)

  layers <- Filter(function(x) !is.null(x) && nrow(x) > 0,
                   list(res$osm_polygons, res$osm_multipolygons))
  if (length(layers) == 0) return(NULL)
  buildings <- do.call(c, lapply(layers, function(x) st_cast(st_geometry(x), "POLYGON")))
  inside <- lengths(st_contains(buildings, pt)) > 0
  if (!any(inside)) return(NULL)

  # OSM can map nested buildings; the smallest one that contains the point is the hall.
  candidates <- buildings[inside]
  st_sf(source = "OpenStreetMap", geometry = candidates[which.min(st_area(candidates))])
}

digitize_outline <- function() {
  if (!interactive()) {
    stop("The venue is not in OSM. Run the script in an interactive session to digitize it.")
  }
  message("Draw the venue outline with the polygon tool and press Done.")
  map <- setView(satellite_basemap(), venue_point[["lon"]], venue_point[["lat"]], zoom = 19)
  drawn <- mapedit::drawFeatures(map = map)
  polygons <- st_geometry(drawn)[st_geometry_type(drawn) %in% c("POLYGON", "MULTIPOLYGON")]
  if (length(polygons) == 0) stop("No polygon was drawn.")
  st_sf(source = "Digitized over Esri World Imagery", geometry = polygons[1])
}

validate_outline <- function(venue) {
  g    <- st_geometry(venue)[1]
  type <- as.character(st_geometry_type(g))
  if (!type %in% c("POLYGON", "MULTIPOLYGON")) {
    stop(sprintf("%s holds a %s and a polygon is required. Delete the file and run again.",
                 outline_path, type))
  }
  area <- as.numeric(st_area(g))
  if (area < min_outline_m2) {
    stop(sprintf("The outline (%s) covers %.0f m2, too small for the hall. Check %s.",
                 venue$source[1], area, outline_path))
  }
  venue[1, ]
}

get_outline <- function() {
  if (file.exists(outline_path)) return(validate_outline(st_read(outline_path, quiet = TRUE)))
  pt <- st_sfc(st_point(c(venue_point[["lon"]], venue_point[["lat"]])), crs = 4326)
  venue <- outline_from_osm(pt)
  if (is.null(venue)) venue <- digitize_outline()
  venue <- validate_outline(venue)
  st_write(venue, outline_path, quiet = TRUE)
  venue
}

# Building local frame ---------------------------------------------------------

# Origin at the southwest corner of the minimum rotated rectangle. d is the long axis
# oriented north, e is d rotated 90 degrees clockwise (east).
local_frame <- function(poly_m) {
  xy <- st_coordinates(st_minimum_rotated_rectangle(poly_m))[1:4, 1:2]
  edges   <- diff(rbind(xy, xy[1, ]))
  edge_len <- sqrt(rowSums(edges^2))
  d <- edges[which.max(edge_len), ] / max(edge_len)
  if (d[2] < 0) d <- -d
  e <- c(d[2], -d[1])
  u <- xy %*% d
  v <- xy %*% e
  list(origin = min(u) * d + min(v) * e, d = d, e = e,
       L = max(u) - min(u), W = max(v) - min(v),
       bearing_deg = atan2(d[1], d[2]) * 180 / pi)
}

local_rect <- function(frame, u0, u1, v0, v1) {
  uv <- rbind(c(u0, v0), c(u1, v0), c(u1, v1), c(u0, v1), c(u0, v0))
  st_polygon(list(sweep(uv[, 1] %o% frame$d + uv[, 2] %o% frame$e, 2, frame$origin, "+")))
}

# Returns c(length, width) of the minimum rotated rectangle, or NA for empty or
# degenerate geometries (a zone outside the outline intersects to GEOMETRYCOLLECTION EMPTY).
rect_sides <- function(g) {
  if (st_is_empty(g)) return(c(NA_real_, NA_real_))
  xy <- st_coordinates(st_minimum_rotated_rectangle(g))[, 1:2, drop = FALSE]
  if (nrow(xy) < 4) return(c(NA_real_, NA_real_))
  sort(sqrt(rowSums(diff(xy[1:3, ])^2)), decreasing = TRUE)
}

# Zones, areas and occupancy ---------------------------------------------------

venue   <- get_outline()
venue_m <- st_geometry(st_transform(venue, crs_m))[[1]]
frame   <- local_frame(venue_m)
cat(sprintf("Outline: %s | long axis %.1f deg from north | bounding rectangle %.1f x %.1f m\n\n",
            venue$source[1], frame$bearing_deg, frame$L, frame$W))

zone_layout <- layout_zones(frame$L, frame$W)
zone_geoms <- lapply(seq_len(nrow(zone_layout)), function(i) {
  r <- local_rect(frame, zone_layout$u0[i], zone_layout$u1[i], zone_layout$v0[i], zone_layout$v1[i])
  z <- st_intersection(r, venue_m)
  # A rectangle that only touches the outline edge leaves lines or points in a collection.
  if (!st_is_empty(z) && inherits(z, "GEOMETRYCOLLECTION")) {
    z <- st_union(st_collection_extract(st_sfc(z), "POLYGON"))[[1]]
  }
  z
})
empty <- vapply(zone_geoms, st_is_empty, logical(1))
if (any(empty)) {
  warning(sprintf("Zones outside the outline: %s. Check layout_zones() or %s.",
                  paste(zone_layout$label[empty], collapse = ", "), outline_path))
}

zones <- st_sf(
  zone     = c("venue", zone_layout$zone),
  label    = c("Whole venue", zone_layout$label),
  geometry = st_sfc(c(list(venue_m), zone_geoms), crs = crs_m)
)
sides <- t(sapply(st_geometry(zones), rect_sides))
zones$length_m <- round(sides[, 1], 1)
zones$width_m  <- round(sides[, 2], 1)
zones$area_m2  <- round(as.numeric(st_area(zones)))
zones$color    <- zone_colors[zones$zone]

floor_free   <- st_difference(st_sfc(venue_m, crs = crs_m),
                              st_union(zones[zones$zone != "venue", ]))
area_free    <- as.numeric(st_area(floor_free))
area_tables  <- sum(zones$area_m2[zones$zone == "tables"])
occupancy <- c(standing = floor(area_free / m2_per_person_standing),
               tables   = floor(area_tables / m2_per_person_tables))

summary_table <- rbind(
  st_drop_geometry(zones)[, c("label", "length_m", "width_m", "area_m2")],
  data.frame(label = "Free floor (standing)", length_m = NA, width_m = NA,
             area_m2 = round(area_free))
)
print(summary_table, row.names = FALSE)
cat(sprintf("\nOccupancy standing: %d (%.2f m2/person) | tables: %d | total: %d\n",
            occupancy[["standing"]], m2_per_person_standing,
            occupancy[["tables"]], sum(occupancy)))

write.csv(summary_table, "salon_olimpico_zones.csv", row.names = FALSE)
zones_ll <- st_transform(zones, 4326)
free_ll  <- st_transform(st_sf(label = "Free floor (standing)", geometry = floor_free), 4326)
st_write(zones_ll, "salon_olimpico_zones.geojson", delete_dsn = TRUE, quiet = TRUE)

# Leaflet map ------------------------------------------------------------------

popup_zone <- sprintf("<b>%s</b><br>%.1f × %.1f m<br>%s m²", zones_ll$label,
                      zones_ll$length_m, zones_ll$width_m,
                      format(zones_ll$area_m2, big.mark = ","))
popup_venue <- paste0(popup_zone[1], "<br>Source: ", venue$source[1])
popup_free  <- sprintf("<b>Free floor (standing)</b><br>%s m²<br>Standing occupancy: %s people",
                       format(round(area_free), big.mark = ","),
                       format(occupancy[["standing"]], big.mark = ","))
inner_ll <- zones_ll[zones_ll$zone != "venue", ]

map <- satellite_basemap() |>
  addPolygons(data = zones_ll[1, ], color = ~color, weight = 3, fillOpacity = 0,
              label = ~label, popup = popup_venue) |>
  addPolygons(data = free_ll, color = "white", weight = 1, dashArray = "4",
              fillColor = "white", fillOpacity = 0.15, label = ~label, popup = popup_free) |>
  addPolygons(data = inner_ll, color = ~color, weight = 2, fillColor = ~color,
              fillOpacity = 0.4, label = ~label, popup = popup_zone[-1]) |>
  addLegend(position = "topright",
            colors = zone_colors[c("venue", "bar", "tables", "stage", "vendors")],
            labels = c("Whole venue", "Alcohol and food", "Tables", "Stage", "Vendors"),
            opacity = 1, title = "Zones") |>
  addScaleBar(position = "bottomleft", options = scaleBarOptions(imperial = FALSE)) |>
  addMeasure(position = "topleft", primaryLengthUnit = "meters",
             primaryAreaUnit = "sqmeters")

# selfcontained = TRUE needs pandoc on some htmlwidgets versions. On error the HTML is
# written with a sibling lib folder.
tryCatch(
  htmlwidgets::saveWidget(map, "salon_olimpico_map.html", selfcontained = TRUE),
  error = function(e) htmlwidgets::saveWidget(map, "salon_olimpico_map.html",
                                              selfcontained = FALSE)
)
map
