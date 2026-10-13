"""Public diagnostic compatibility imports; production uses the shared matcher."""
from app.arrivals.matching import (normalize_name, distance_meters, match_route, direction_candidate,
                                  arrival_direction_matches, boarding_candidates, station_route_scopes, scoped_matches)
