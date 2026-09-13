/**
 * SkyGuard AI - Geospatial Utilities
 * Haversine geodesic distance, buddy station ranking, and spatial geometry
 */

export function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0; // Earth mean radius in kilometers
  const toRad = (d: number) => (d * Math.PI) / 180.0;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export interface GeoPoint {
  latitude: number;
  longitude: number;
  station_id: string;
  [key: string]: any;
}

export function findNearestNeighbors<T extends GeoPoint>(
  target: GeoPoint,
  allStations: T[],
  k: number = 5,
  maxRadiusKm: number = 300.0
): Array<T & { distance_km: number }> {
  const ranked = allStations
    .filter(s => s.station_id !== target.station_id && s.latitude && s.longitude)
    .map(s => {
      const d = haversineKm(target.latitude, target.longitude, s.latitude, s.longitude);
      return { ...s, distance_km: Math.round(d * 10) / 10 };
    })
    .filter(s => s.distance_km <= maxRadiusKm)
    .sort((a, b) => a.distance_km - b.distance_km);

  return ranked.slice(0, k);
}

export const REGIONAL_BOUNDS: Record<string, { minLat: number; maxLat: number; minLon: number; maxLon: number }> = {
  NORTH_INDIA: { minLat: 24.0, maxLat: 37.5, minLon: 72.0, maxLon: 84.0 },
  SOUTH_INDIA: { minLat: 8.0, maxLat: 20.0, minLon: 74.0, maxLon: 86.0 },
  EAST_INDIA: { minLat: 20.0, maxLat: 29.5, minLon: 84.0, maxLon: 97.5 },
  WEST_CENTRAL: { minLat: 18.0, maxLat: 26.0, minLon: 68.0, maxLon: 82.0 },
};
