import { priceMonitorAllowed } from '@/lib/server/price-monitor-access';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const exec = promisify(execFile);

export async function GET(request: Request) {
  if (!await priceMonitorAllowed()) {
    return Response.json({ error: 'forbidden' }, { status: 403 });
  }

  const params = new URL(request.url).searchParams;
  const language = params.get('language') || 'de';
  const scope = params.get('scope') || 'current';
  const kind = params.get('kind') || 'karten';
  const format = params.get('format') || 'json';
  const page = Number(params.get('page') || '0');
  const search = (params.get('search') || '').slice(0, 120);
  if (
    !['de', 'en'].includes(language) ||
    !['all', 'current'].includes(scope) ||
    !['karten', 'preise', 'technik', 'drucke', 'alle'].includes(kind) ||
    !['json', 'csv'].includes(format) ||
    !Number.isInteger(page) || page < 0 || page > 2000
  ) {
    return Response.json({ error: 'invalid_query' }, { status: 400 });
  }

  try {
    const exporting = format === 'csv';
    const { stdout } = await exec('python3', [
      '/home/tv/cardshop/scripts/cardmarket/admin/cardmarket-live-failures.py',
      '--language', language, '--scope', scope, '--kind', kind,
      '--page', String(page), '--search=' + search, '--format', format,
    ], {
      timeout: exporting ? 60000 : 20000,
      maxBuffer: exporting ? 64 * 1024 * 1024 : 200000,
    });

    if (exporting) {
      const date = new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Berlin' });
      const filename = ['offene-pruefungen', language, scope, kind, date].join('-') + '.csv';
      return new Response(stdout, {
        headers: {
          'Content-Type': 'text/csv; charset=utf-8',
          'Content-Disposition': 'attachment; filename="' + filename + '"',
          'Cache-Control': 'private, no-store',
        },
      });
    }

    return Response.json(JSON.parse(stdout), { headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return Response.json({ error: 'scan_failure_list_unavailable' }, { status: 503 });
  }
}
