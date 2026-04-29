import { NextResponse } from 'next/server';

type ControlAction = 'start' | 'stop' | 'skip' | 'reload';

function isValidAction(action: unknown): action is ControlAction {
  return action === 'start' || action === 'stop' || action === 'skip' || action === 'reload';
}

async function proxyControl(action: ControlAction) {
  const controlUrl = process.env.LIQUIDSOAP_CONTROL_URL;
  if (!controlUrl) {
    return {
      ok: true,
      mode: 'placeholder' as const,
      message: `Action ${action} simulée (LIQUIDSOAP_CONTROL_URL non configurée).`,
    };
  }

  const authToken = process.env.LIQUIDSOAP_CONTROL_TOKEN;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const res = await fetch(controlUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify({ action }),
    cache: 'no-store',
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`Control proxy failed ${res.status}: ${text.slice(0, 160)}`);
  }

  return {
    ok: true,
    mode: 'live' as const,
    message: text || `Action ${action} envoyée à Liquidsoap.`,
  };
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const action = (body as Record<string, unknown>).action;

    if (!isValidAction(action)) {
      return NextResponse.json({ error: 'Action invalide. Utiliser start|stop|skip|reload' }, { status: 400 });
    }

    const result = await proxyControl(action);
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
