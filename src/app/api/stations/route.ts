import { NextRequest, NextResponse } from 'next/server';
import { readStationCatalog } from '@/server/stations';
export const dynamic = 'force-dynamic';
export async function GET(request: NextRequest) {
  const network = request.nextUrl.searchParams.get('network') || 'all';
  const zone = request.nextUrl.searchParams.get('climate_zone') || 'all';
  let rows = readStationCatalog();
  if (network === 'benchmark') rows = rows.filter(s => s.is_benchmark);
  if (network === 'active') rows = rows.filter(s => s.is_active_2024_plus);
  if (zone.toLowerCase() !== 'all') rows = rows.filter(s => s.climate_zone?.toLowerCase() === zone.toLowerCase());
  return NextResponse.json(rows);
}
