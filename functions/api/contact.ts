interface Env {
  RESEND_API_KEY?: string;
  CONTACT_TO_EMAIL?: string;
  CONTACT_FROM_EMAIL?: string;
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}

export async function onRequestPost(context: { request: Request; env: Env }) {
  const { request, env } = context;

  try {
    const data = (await request.json()) as {
      name?: string;
      email?: string;
      need?: string;
      message?: string;
      company?: string;
      hp_website?: string;
    };

    // Honeypot defense: immediately drop bot submissions
    if (data.company || data.hp_website) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    const { name, email, need, message } = data;
    if (!name || !email || !message) {
      return new Response(JSON.stringify({ ok: false, error: "Missing required fields" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (!env.RESEND_API_KEY || !env.CONTACT_TO_EMAIL) {
      return new Response(JSON.stringify({ ok: false, fallback: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    const from = env.CONTACT_FROM_EMAIL || "Synex Labs <onboarding@resend.dev>";

    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from,
        to: [env.CONTACT_TO_EMAIL],
        reply_to: email,
        subject: `New brief: ${need || "Project"} from ${name}`,
        text: `Name: ${name}\nEmail: ${email}\nLooking for: ${need || "Website"}\n\n${message}`,
      }),
    });

    if (res.ok) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ ok: false, fallback: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return new Response(JSON.stringify({ ok: false, fallback: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
}
