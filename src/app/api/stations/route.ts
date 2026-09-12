import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export interface StationRecord {
  station_id: string;
  station_name: string;
  climate_zone: string;
  cluster: string;
  evaluation_role: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  icao?: string;
  is_benchmark: boolean;
  is_active_2024_plus: boolean;
  status?: string;
}

function parseStationsCSV(filePath: string): StationRecord[] {
  if (!fs.existsSync(filePath)) return [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split(/\r?\n/).filter(line => line.trim().length > 0);
  if (lines.length <= 1) return [];

  const headers = lines[0].split(',').map(h => h.trim());
  const rows: StationRecord[] = [];

  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map(c => c.trim());
    if (cols.length < headers.length) continue;

    const rowObj: Record<string, string> = {};
    headers.forEach((h, idx) => {
      rowObj[h] = cols[idx];
    });

    rows.push({
      station_id: rowObj['station_id'],
      station_name: rowObj['station_name'] || rowObj['station_id'],
      climate_zone: rowObj['climate_zone'] || 'Unknown',
      cluster: rowObj['cluster'] || 'national',
      evaluation_role: rowObj['evaluation_role'] || 'general',
      latitude: parseFloat(rowObj['latitude']) || 0,
      longitude: parseFloat(rowObj['longitude']) || 0,
      elevation_m: parseFloat(rowObj['elevation_m']) || 0,
      icao: rowObj['icao'] || '',
      is_benchmark: rowObj['is_benchmark'] === '1' || rowObj['is_benchmark'] === 'true',
      is_active_2024_plus: rowObj['is_active_2024_plus'] === '1' || rowObj['is_active_2024_plus'] === 'true',
      status: 'NORMAL'
    });
  }

  return rows;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const network = searchParams.get('network') || 'all';
  const climateZone = searchParams.get('climate_zone') || '';

  // Try external API if configured
  const mlUrl = process.env.SKYGUARD_API_URL;
  if (mlUrl) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);
      const res = await fetch(`${mlUrl}/api/stations?network=${encodeURIComponent(network)}&climate_zone=${encodeURIComponent(climateZone)}`, {
        signal: controller.signal,
        cache: 'no-store'
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through to local CSV file
    }
  }

  const csvPath = path.join(process.cwd(), 'config', 'all_india_aws_network.csv');
  let stations = parseStationsCSV(csvPath);

  if (network === 'benchmark') {
    stations = stations.filter(s => s.is_benchmark);
  } else if (network === 'active') {
    stations = stations.filter(s => s.is_active_2024_plus);
  }

  if (climateZone && climateZone.toLowerCase() !== 'all') {
    stations = stations.filter(s => s.climate_zone.toLowerCase() === climateZone.toLowerCase());
  }

  return NextResponse.json(stations);
}
