import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') || '100', 10);
  const mlUrl = process.env.SKYGUARD_API_URL;

  // Try external API first
  if (mlUrl) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(`${mlUrl}/api/incidents?limit=${limit}&mode=live`, {
        signal: controller.signal,
        cache: 'no-store'
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const incidents = await res.json();
        if (Array.isArray(incidents) && incidents.length > 0) {
          return NextResponse.json(incidents);
        }
      }
    } catch {
      // Fall through to historical incident dataset
    }
  }

  // Read time_test_incidents.jsonl.gz
  const gzPath = path.join(process.cwd(), 'data', 'incidents', 'time_test_incidents.jsonl.gz');
  if (!fs.existsSync(gzPath)) {
    return NextResponse.json([]);
  }

  try {
    const fileBuffer = fs.readFileSync(gzPath);
    const decompressed = zlib.gunzipSync(fileBuffer).toString('utf-8');
    const lines = decompressed.split('\n').filter(l => l.trim().length > 0);
    const incidents = [];

    for (const line of lines) {
      if (incidents.length >= limit) break;
      try {
        incidents.push(JSON.parse(line));
      } catch {
        // Skip malformed lines
      }
    }

    return NextResponse.json(incidents);
  } catch (err) {
    return NextResponse.json({ error: 'Failed to read incidents store' }, { status: 500 });
  }
}
