/**
 * Browser MSW setup.
 *
 * This worker only registers customer/portfolio demo handlers. Market indices,
 * symbol search/quotes, market leaders, news, watchlist, and Copilot are left
 * to the real backend/API.
 */
import { setupWorker } from "msw/browser";
import {
  portfolioAiInsightHandler,
  portfolioClientsHandler,
  portfolioCreateHoldingHandler,
  portfolioHoldingsHandler,
  portfolioMonthlyReturnsHandler,
  portfolioRebalanceHandler,
  portfolioSectorHeatmapHandler,
  portfolioSnapshotsHandler,
  portfolioSummaryHandler,
} from "./dashboard";

export const worker = setupWorker(
  portfolioClientsHandler,
  portfolioHoldingsHandler,
  portfolioCreateHoldingHandler,
  portfolioSummaryHandler,
  portfolioSnapshotsHandler,
  portfolioSectorHeatmapHandler,
  portfolioMonthlyReturnsHandler,
  portfolioAiInsightHandler,
  portfolioRebalanceHandler,
);
