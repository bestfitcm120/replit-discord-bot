import { Router, Request, Response } from "express";
import { createHmac, randomBytes } from "crypto";

const router = Router();

const DISCORD_API = "https://discord.com/api/v10";
const SESSION_COOKIE = "modbot_session";
const COOKIE_MAX_AGE = 7 * 24 * 60 * 60 * 1000;

function getSessionSecret(): string {
  return process.env["SESSION_SECRET"] ?? "dev-secret-change-in-production";
}

function signPayload(payload: object): string {
  const data = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = createHmac("sha256", getSessionSecret()).update(data).digest("base64url");
  return `${data}.${sig}`;
}

function verifyToken(token: string): object | null {
  try {
    const [data, sig] = token.split(".");
    const expected = createHmac("sha256", getSessionSecret()).update(data).digest("base64url");
    if (sig !== expected) return null;
    return JSON.parse(Buffer.from(data, "base64url").toString("utf8"));
  } catch {
    return null;
  }
}

function getSession(req: Request): Record<string, unknown> | null {
  const token = req.cookies?.[SESSION_COOKIE];
  if (!token) return null;
  return verifyToken(token) as Record<string, unknown> | null;
}

function setSession(res: Response, data: object): void {
  const token = signPayload(data);
  res.cookie(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: COOKIE_MAX_AGE,
    secure: process.env["SECURE_COOKIES"] === "true",
  });
}

function clearSession(res: Response): void {
  res.clearCookie(SESSION_COOKIE);
}

function getRedirectUri(): string {
  const base = process.env["BASE_URL"] ?? `http://localhost:${process.env["PORT"] ?? 5000}`;
  return `${base}/api/auth/discord/callback`;
}

// GET /api/auth/discord — redirect to Discord OAuth
router.get("/discord", (_req: Request, res: Response) => {
  const clientId = process.env["DISCORD_CLIENT_ID"] ?? "";
  const redirectUri = encodeURIComponent(getRedirectUri());
  const url = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=identify%20guilds`;
  res.redirect(url);
});

// GET /api/auth/discord/callback
router.get("/discord/callback", async (req: Request, res: Response) => {
  const code = req.query["code"] as string | undefined;
  if (!code) {
    res.redirect("/?error=no_code");
    return;
  }

  try {
    const tokenRes = await fetch(`${DISCORD_API}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: process.env["DISCORD_CLIENT_ID"] ?? "",
        client_secret: process.env["DISCORD_CLIENT_SECRET"] ?? "",
        grant_type: "authorization_code",
        code,
        redirect_uri: getRedirectUri(),
      }),
    });

    const tokenData = await tokenRes.json() as { access_token?: string; refresh_token?: string };
    if (!tokenData.access_token) {
      res.redirect("/?error=token_exchange_failed");
      return;
    }

    const userRes = await fetch(`${DISCORD_API}/users/@me`, {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    });
    const user = await userRes.json() as { id: string; username: string; discriminator?: string; avatar?: string };

    setSession(res, {
      userId: user.id,
      username: user.username,
      discriminator: user.discriminator ?? "0",
      avatar: user.avatar ?? null,
      accessToken: tokenData.access_token,
    });

    res.redirect("/servers");
  } catch (err) {
    req.log.error({ err }, "OAuth callback failed");
    res.redirect("/?error=oauth_failed");
  }
});

// GET /api/auth/me
router.get("/me", (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) {
    res.status(401).json({ error: "Not authenticated" });
    return;
  }
  const userId = session["userId"] as string;
  const avatar = session["avatar"] as string | null;
  const avatarUrl = avatar
    ? `https://cdn.discordapp.com/avatars/${userId}/${avatar}.png`
    : `https://cdn.discordapp.com/embed/avatars/${parseInt(userId) % 5}.png`;

  res.json({
    id: userId,
    username: session["username"],
    discriminator: session["discriminator"] ?? "0",
    avatar,
    avatarUrl,
  });
});

// POST /api/auth/logout
router.post("/logout", (req: Request, res: Response) => {
  clearSession(res);
  res.json({ message: "Logged out" });
});

export { getSession };
export default router;
