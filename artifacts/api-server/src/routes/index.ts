import { Router, type IRouter } from "express";
import healthRouter from "./health";
import authRouter from "./auth";
import guildsRouter from "./guilds";
import { getBotInviteUrl } from "./bot";

const router: IRouter = Router();

router.use(healthRouter);
router.use("/auth", authRouter);
router.use("/guilds", guildsRouter);

// Bot invite URL
router.get("/bot/invite", (_req, res) => {
  res.json({ url: getBotInviteUrl() });
});

export default router;
