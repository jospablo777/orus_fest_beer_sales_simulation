# Estimation, time-series and counterfactual analysis of the simulation outputs.
#
# Inputs:  output/runs/calibration_draws.csv, posterior_draws.csv, scenario_metrics.csv,
#          scenario_series.csv, scenario_waits.csv, scenario_labels.csv;
#          output/tables/staffing_reliability.csv, staffing_plan.csv (scripts/run_staffing.py);
#          config/*.yaml
# Outputs: output/figures/*.png, output/tables/*.csv
#
# Run from the project root in a UTF-8 locale: LC_ALL=C.UTF-8 Rscript analysis/figures.R

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(patchwork)
  library(scales)
  library(yaml)
})

runs_dir <- "output/runs"
fig_dir  <- "output/figures"
tab_dir  <- "output/tables"
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(tab_dir, showWarnings = FALSE, recursive = TRUE)
set.seed(2026)

# Bytes are read as UTF-8 without re-encoding, so the result does not depend on the locale.
read_cfg <- function(path) {
  yaml::yaml.load(paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n"))
}
base_cfg   <- read_cfg("config/base.yaml")
report_cfg <- read_cfg("config/report.yaml")
cal_cfg    <- read_cfg("config/calibration.yaml")
stf_cfg    <- read_cfg("config/staffing.yaml")
svc_window <- sprintf("%s–%s", stf_cfg$service_target$window$from, stf_cfg$service_target$window$to)
price      <- report_cfg$beer_price_mxn
headline   <- report_cfg$headline_scenario

# Colors from the Orus Fest 2026 promotion art; same values as sim/theme.py and the site.
paper  <- "#100d0c"
ink    <- "#ece4d6"   # bone white
muted  <- "#a69c8c"
gridc  <- "#2c2522"
grey   <- "#8e939b"   # neutral: references, other options
bronze <- "#bd8a35"   # recommended setup
red    <- "#c42a3c"   # 2026 setup, limits
blue   <- "#3586c6"   # steel blue: second measure in a figure

theme_set(
  theme_minimal(base_size = 14) +
    theme(plot.background = element_rect(fill = paper, colour = NA),
          panel.background = element_rect(fill = paper, colour = NA),
          text = element_text(colour = ink),
          plot.title = element_text(face = "bold", colour = ink),
          plot.subtitle = element_text(colour = muted, size = rel(0.85)),
          plot.caption = element_text(colour = muted, hjust = 0),
          axis.text = element_text(colour = muted),
          axis.title = element_text(colour = ink),
          panel.grid.major = element_line(colour = gridc),
          panel.grid.minor = element_blank(),
          strip.text = element_text(face = "bold", colour = ink),
          legend.text = element_text(colour = ink),
          legend.title = element_text(colour = ink),
          legend.position = "bottom")
)

clock_to_min <- function(x) {
  p <- as.integer(strsplit(x, ":", fixed = TRUE)[[1]])
  m <- 60L * p[1] + p[2]
  if (p[1] < 8L) m + 1440L else m
}
fmt_clock <- function(m) sprintf("%02d:%02d", (m %/% 60) %% 24, round(m %% 60))
scale_clock <- function(from = 13 * 60, to = 27 * 60, by = 120) {
  scale_x_continuous(breaks = seq(from, to, by), labels = fmt_clock)
}
save_fig <- function(p, name, w = 10, h = 6) {
  ggsave(file.path(fig_dir, name), p, width = w, height = h, dpi = 150, bg = paper)
}
# 95% percentile bootstrap interval for the median of x.
boot_median_ci <- function(x, n_boot = 4000) {
  x <- x[is.finite(x)]
  if (length(x) < 3) return(c(NA_real_, NA_real_))
  m <- matrix(sample(x, n_boot * length(x), replace = TRUE), nrow = n_boot)
  unname(quantile(apply(m, 1, median), c(0.025, 0.975)))
}
# Exact (Clopper-Pearson) 95% interval for a share of k out of n.
exact_ci <- function(k, n) as.numeric(binom.test(k, n)$conf.int)
wrap <- function(x, width = 30) {
  vapply(x, function(s) paste(strwrap(s, width), collapse = "\n"), "", USE.NAMES = FALSE)
}

sched_all <- rbindlist(lapply(base_cfg$schedule, function(a) {
  data.table(act = a$act, kind = if (is.null(a$kind)) "band" else a$kind,
             start = clock_to_min(a$start), end = clock_to_min(a$end))
}))
sched <- sched_all[kind == "band"]
set_layer <- function(alpha = 0.14) {
  annotate("rect", xmin = sched$start, xmax = sched$end, ymin = -Inf, ymax = Inf,
           fill = "#8C3CFF", alpha = alpha)
}

# -----------------------------------------------------------------------------------------
# 1. Calibration as estimation: which unknowns are consistent with what was observed
# -----------------------------------------------------------------------------------------

cal  <- fread(file.path(runs_dir, "calibration_draws.csv"))   # every simulated night
post <- fread(file.path(runs_dir, "posterior_draws.csv"))     # weighted resample of the matches
prior_names <- names(cal_cfg$priors)
is_float <- vapply(cal_cfg$priors, function(p) p$type == "float", logical(1))
floats  <- prior_names[is_float]
choices <- prior_names[!is_float]
pretty_name <- c(
  "crowd.changeover_boost" = "Thirst boost between sets",
  "crowd.acts_before_mean" = "Acts attended before the core act",
  "crowd.acts_after_mean" = "Acts attended after the core act",
  "crowd.whole_event_share" = "Share staying to the end",
  "crowd.afternoon_thirst_mult" = "Drinking pace before 18:00",
  "crowd.drinker_share" = "Share who drink beer",
  "crowd.rate_mean_per_h" = "Beers per hour per drinker",
  "crowd.patience_median_min" = "Median patience (min)",
  "crowd.group_size_mean" = "Friends per group (mean)",
  "bar.n_pour" = "People serving beer",
  "bar.s_cash_mean_s" = "Ticket window, s per buyer",
  "bar.s_pour_mean_s" = "Serving time, first beer (s)",
  "bar.extra_beer_factor" = "Time of each extra beer (share)",
  "bar.bundle_mean" = "Spare tickets per visit, plus 1"
)
lab <- function(x) ifelse(is.na(pretty_name[x]), x, pretty_name[x])

post_long <- melt(post[, ..floats], measure.vars = floats)
post_long[, label := lab(as.character(variable))]
prior_dt <- rbindlist(lapply(floats, function(f) {
  p <- cal_cfg$priors[[f]]
  data.table(label = lab(f), low = p$low, high = p$high, dens = 1 / (p$high - p$low))
}))
p_post <- ggplot() +
  geom_rect(data = prior_dt, aes(xmin = low, xmax = high, ymin = 0, ymax = dens),
            fill = grey, alpha = 0.4) +
  geom_histogram(data = post_long, aes(value, after_stat(density)), bins = 10,
                 fill = bronze, alpha = 0.9) +
  facet_wrap(~label, scales = "free", ncol = 4, labeller = label_wrap_gen(22)) +
  labs(title = "What the 2026 observations say about the unknowns",
       subtitle = sprintf("Grey is the range tried for each unknown. Bronze is the %d nights that match 2026 (%d simulated in %d stages).",
                          nrow(post), nrow(cal), max(cal$stage) + 1),
       x = NULL, y = "density") +
  theme(axis.text.y = element_blank(), strip.text = element_text(size = rel(0.8)))
pour_share <- post[, .(share = .N / nrow(post)), by = .(value = `bar.n_pour`)]
p_pour <- ggplot(pour_share, aes(factor(value), share)) +
  geom_hline(yintercept = 1 / length(cal_cfg$priors$bar.n_pour$values), colour = grey,
             linetype = 2) +
  geom_col(fill = bronze, width = 0.6) +
  scale_y_continuous(labels = percent) +
  labs(subtitle = "People serving beer in the matching nights. The dashed line is the share tried.",
       x = "people serving beer", y = "share of matching nights")
save_fig(p_post / p_pour + plot_layout(heights = c(3, 1)), "01_calibration_posterior.png",
         w = 11, h = 11)

w_acc <- cal[accepted == TRUE, weight]
cal_summary <- data.table(
  simulations = nrow(cal), stages = max(cal$stage) + 1L, matching = sum(cal$accepted),
  effective_sample = sum(w_acc)^2 / sum(w_acc^2), posterior_draws = nrow(post),
  peak_occupancy_median = median(post$peak_occupancy),
  peak_occupancy_p05 = quantile(post$peak_occupancy, 0.05),
  peak_occupancy_p95 = quantile(post$peak_occupancy, 0.95),
  exchange_wait_median = median(post$obs_exchange_median_min),
  buyer_wait_median = median(post$obs_buyer_median_min),
  night_exchange_wait_median = median(post$night_exchange_median_min),
  early_wait_median = median(post$early_median_min),
  ticket_line_median = median(post$queue_cash_obs),
  exchange_line_median = median(post$queue_pour_obs),
  beers_2026_median = median(post$beers_total),
  beers_2026_p05 = quantile(post$beers_total, 0.05),
  beers_2026_p95 = quantile(post$beers_total, 0.95)
)
fwrite(cal_summary, file.path(tab_dir, "calibration_summary.csv"))

# Regression metamodels on every simulated night, predictors standardized (effect of +1 SD).
z <- function(x) (x - mean(x)) / sd(x)
# Inputs that vary in d; a constant input has no effect to estimate.
varying <- function(d, cols) {
  cols[vapply(cols, function(cn) isTRUE(sd(as.numeric(d[[cn]])) > 0), logical(1))]
}
coef_table <- function(fit) {
  s <- summary(fit)$coefficients
  ci <- suppressMessages(confint.default(fit))[rownames(s), , drop = FALSE]
  out <- data.table(term = gsub("`", "", rownames(s)), estimate = s[, 1], lo = ci[, 1],
                    hi = ci[, 2], p = s[, 4])
  out[term != "(Intercept)"]
}
rhs <- function(cols) paste(sprintf("`%s`", cols), collapse = " + ")
ok <- cal[is.finite(obs_exchange_median_min)]
reg_cols <- varying(ok, prior_names)
X <- ok[, lapply(.SD, function(v) z(as.numeric(v))), .SDcols = reg_cols]
dat <- cbind(X, wait = ok$obs_exchange_median_min, ticket = ok$queue_cash_obs,
             exchange = ok$queue_pour_obs)
form_rhs <- rhs(reg_cols)
fits <- list(
  "Wait in the exchange line, 18:00–20:00 (min)" = lm(as.formula(paste("wait ~", form_rhs)), dat),
  "People in the ticket line, 18:00–20:00" = lm(as.formula(paste("ticket ~", form_rhs)), dat),
  "People in the exchange lines, 18:00–20:00" = lm(as.formula(paste("exchange ~", form_rhs)), dat))
ct <- rbindlist(lapply(names(fits), function(n) {
  cbind(coef_table(fits[[n]]), model = n, r2 = summary(fits[[n]])$r.squared)
}))
ct[, term := lab(term)]
fwrite(ct, file.path(tab_dir, "calibration_regressions.csv"))
p_reg <- ggplot(ct, aes(estimate, reorder(term, abs(estimate)))) +
  geom_vline(xintercept = 0, colour = grey) +
  geom_errorbar(aes(xmin = lo, xmax = hi), orientation = "y", width = 0, colour = bronze, linewidth = 1) +
  geom_point(colour = bronze, size = 2.6) +
  facet_wrap(~model, scales = "free_x", labeller = label_wrap_gen(24)) +
  labs(title = "Which unknowns drive each line in the 2026 setup",
       subtitle = sprintf("Linear regressions over %d simulated nights.\nEffect of +1 standard deviation with 95%% CI. R² = %s.",
                          nrow(ok), paste(sprintf("%.2f", unique(ct$r2)), collapse = ", ")),
       x = NULL, y = NULL)
save_fig(p_reg, "02_calibration_regressions.png", w = 11, h = 6.5)

# -----------------------------------------------------------------------------------------
# 2. Scenario outputs
# -----------------------------------------------------------------------------------------

met    <- fread(file.path(runs_dir, "scenario_metrics.csv"))
ser    <- fread(file.path(runs_dir, "scenario_series.csv"))
waits  <- fread(file.path(runs_dir, "scenario_waits.csv"))
labels <- fread(file.path(runs_dir, "scenario_labels.csv"))
lab_of <- setNames(labels$label, labels$scenario)
n_draws <- uniqueN(met$draw)
main_order <- labels[family == "main" & scenario != "baseline", scenario]

outcomes <- c(evening_p90_min = sprintf("Wait of 1 in 10 buyers, %s (min)", svc_window),
              beers_total = "Beers sold",
              lost_attempts = "Purchase attempts abandoned",
              headliner_min_per_buyer = "Headliner minutes in line per buyer",
              line_hours = "Hours in line, everyone added up")
b0 <- met[scenario == "baseline", c("draw", names(outcomes)), with = FALSE]
setnames(b0, names(outcomes), paste0(names(outcomes), "_0"))
cf <- merge(met[scenario != "baseline"], b0, by = "draw")
for (o in names(outcomes)) cf[, (paste0("d_", o)) := get(o) - get(paste0(o, "_0"))]

# Effect of each setup against 2026 on the same night. `med_lo`, `med_hi`: 95% bootstrap
# interval of the median effect. `lo`, `hi`: 5% to 95% of the nights.
eff <- rbindlist(lapply(names(outcomes), function(o) {
  cf[, {
    d <- get(paste0("d_", o))
    better <- if (o == "beers_total") d > 0 else d < 0
    ci <- boot_median_ci(d)
    ex <- exact_ci(sum(better), .N)
    .(outcome = outcomes[[o]], med = median(d), med_lo = ci[1], med_hi = ci[2],
      lo = quantile(d, 0.05), hi = quantile(d, 0.95), improved_n = sum(better), n = .N,
      improved = mean(better), improved_lo = ex[1],
      p_wilcoxon = suppressWarnings(wilcox.test(d)$p.value))
  }, by = .(scenario, family, label)]
}))
fwrite(eff, file.path(tab_dir, "counterfactual_effects.csv"))

# Same-night differences between pairs of setups (second minus first).
pairs <- list(c("pay_at_tap", headline), c(headline, "full_setup"), c("pay_at_tap", "cashless"),
              c("more_cashiers", headline))
cmp <- rbindlist(lapply(pairs, function(pr) {
  a <- met[scenario == pr[1]][order(draw)]
  b <- met[scenario == pr[2]][order(draw)]
  rbindlist(lapply(c("evening_p90_min", "beers_total"), function(o) {
    d <- b[[o]] - a[[o]]
    ci <- boot_median_ci(d)
    data.table(first = pr[1], second = pr[2], outcome = o, med = median(d), med_lo = ci[1],
               med_hi = ci[2], p_wilcoxon = suppressWarnings(wilcox.test(d)$p.value),
               staff_diff = median(b$staff - a$staff),
               staff_hours_diff = median(b$staff_hours - a$staff_hours))
  }))
}))
fwrite(cmp, file.path(tab_dir, "comparisons.csv"))

# Sensitivity to the line threshold of the calibration: nights with at least 30 people in
# each line against nights with 20 to 30.
strict <- post[, .(draw, strict = queue_cash_obs >= 30 & queue_pour_obs >= 30)]
thr <- merge(cf[scenario == headline], strict, by = "draw")[, .(
  nights = .N, wait_2026 = median(evening_p90_min_0), wait_plan = median(evening_p90_min),
  extra_beers = median(d_beers_total)), by = strict][order(-strict)]
fwrite(thr, file.path(tab_dir, "threshold_check.csv"))

eff_main <- eff[family == "main" & outcome %in% outcomes[1:3]]
eff_main[, label := factor(wrap(label, 34), levels = rev(wrap(lab_of[main_order], 34)))]
eff_main[, outcome := factor(outcome, levels = outcomes[1:3])]
p_cf <- ggplot(eff_main, aes(med, label)) +
  geom_vline(xintercept = 0, colour = grey) +
  geom_errorbar(aes(xmin = lo, xmax = hi), orientation = "y", width = 0, colour = bronze, linewidth = 0.7,
                 alpha = 0.6) +
  geom_errorbar(aes(xmin = med_lo, xmax = med_hi), orientation = "y", width = 0, colour = bronze,
                 linewidth = 2.2) +
  geom_point(colour = ink, size = 1.8) +
  facet_wrap(~outcome, scales = "free_x", ncol = 3, labeller = label_wrap_gen(22)) +
  labs(title = "Effect of each setup against 2026, same night",
       subtitle = sprintf("Dots are median changes over %d nights. Thick bars are the 95%% interval of the median\nand thin bars span 5%% to 95%% of the nights.",
                          n_draws),
       x = "change against the 2026 setup", y = NULL)
save_fig(p_cf, "05_counterfactual_effects.png", w = 11, h = 7)

# 2026 counterfactual in beers and money for the plan.
extra <- cf[scenario == headline, d_beers_total]
ci <- boot_median_ci(extra)
rev_tab <- data.table(median_extra_beers = median(extra), med_lo = ci[1], med_hi = ci[2],
                      p05 = quantile(extra, 0.05), p95 = quantile(extra, 0.95), price_mxn = price)
fwrite(rev_tab, file.path(tab_dir, "counterfactual_2026_revenue.csv"))

# Staff on beer and extra beers per extra staff hour under the plan (plan minus 2026, same
# night). Staff hours count every person serving, the ticket window and the sellers.
st <- merge(met[scenario == headline, .(draw, staff, staff_hours, beers_total)],
            met[scenario == "baseline", .(draw, staff_0 = staff, staff_hours_0 = staff_hours,
                                          beers_0 = beers_total)], by = "draw")
st[, extra_hours := staff_hours - staff_hours_0]
st[, per_hour := (beers_total - beers_0) / extra_hours]
ci <- boot_median_ci(st$per_hour)
staff_tab <- data.table(
  staff_2026 = median(st$staff_0), staff_2026_lo = quantile(st$staff_0, 0.05),
  staff_2026_hi = quantile(st$staff_0, 0.95), staff_plan = median(st$staff),
  hours_2026 = median(st$staff_hours_0), hours_plan = median(st$staff_hours),
  extra_hours = median(st$extra_hours), beers_per_extra_hour = median(st$per_hour),
  med_lo = ci[1], med_hi = ci[2], p05 = quantile(st$per_hour, 0.05),
  p95 = quantile(st$per_hour, 0.95), nights = nrow(st), price_mxn = price)
fwrite(staff_tab, file.path(tab_dir, "staff_sales.csv"))

# People inside and people in each line through the night.
band <- function(d, col) d[, .(med = median(get(col)), lo = quantile(get(col), 0.05),
                                hi = quantile(get(col), 0.95),
                                lo50 = quantile(get(col), 0.25), hi50 = quantile(get(col), 0.75)),
                           by = .(scenario, clock_min)]
occ <- band(ser[scenario == "baseline"], "occupancy")
p_occ <- ggplot(occ, aes(clock_min)) +
  set_layer() +
  geom_ribbon(aes(ymin = lo, ymax = hi), fill = bronze, alpha = 0.15) +
  geom_ribbon(aes(ymin = lo50, ymax = hi50), fill = bronze, alpha = 0.3) +
  geom_line(aes(y = med), colour = bronze, linewidth = 1) +
  annotate("text", x = (sched$start + sched$end) / 2, y = Inf, label = sched$act, angle = 90,
           hjust = 1.05, size = 3.3, colour = "#b48cff") +
  scale_clock() +
  labs(title = "Estimated people inside the hall, 2026",
       subtitle = sprintf("Median with 50%% and 90%% bands over %d nights. Purple spans are band sets and the gaps between them are DJ sets.", n_draws),
       x = NULL, y = "people inside")
lines_dt <- rbind(
  band(ser[scenario == "baseline"], "queue_cash")[, series := "2026, ticket line"],
  band(ser[scenario == "baseline"], "queue_pour")[, series := "2026, exchange lines"],
  band(ser[scenario == headline], "in_lines_total")[, series := "Plan, all lines"])
lines_dt[, series := factor(series, levels = c("2026, ticket line", "2026, exchange lines",
                                               "Plan, all lines"))]
p_lines <- ggplot(lines_dt, aes(clock_min, colour = series, fill = series)) +
  set_layer() +
  geom_ribbon(aes(ymin = lo50, ymax = hi50), alpha = 0.2, colour = NA) +
  geom_line(aes(y = med), linewidth = 1) +
  scale_colour_manual(NULL, values = c(red, blue, bronze)) +
  scale_fill_manual(NULL, values = c(red, blue, bronze)) +
  scale_clock() +
  labs(title = "People standing in each line",
       subtitle = "Median and middle half of the nights", x = NULL, y = "people")
save_fig(p_occ / p_lines, "03_time_series_occupancy_lines.png", w = 11, h = 9.5)

# Time in line by time of joining.
wsum <- waits[, .(med = median(median), lo = quantile(median, 0.1), hi = quantile(median, 0.9)),
              by = .(scenario, clock_min)]
base_w <- wsum[scenario == "baseline", .(clock_min, base_med = med)]
wk <- merge(wsum[scenario %in% main_order], base_w, by = "clock_min")
wk[, label := factor(lab_of[scenario], levels = lab_of[main_order])]
p_wait <- ggplot(wk, aes(clock_min)) +
  set_layer(0.1) +
  geom_line(aes(y = base_med), colour = red, linewidth = 0.8) +
  geom_ribbon(aes(ymin = lo, ymax = hi), fill = bronze, alpha = 0.25) +
  geom_line(aes(y = med), colour = bronze, linewidth = 1) +
  facet_wrap(~label, ncol = 3, labeller = label_wrap_gen(30)) +
  scale_clock(by = 180) +
  labs(title = "Typical time in line by time of joining",
       subtitle = "Bronze shows each setup (median night and 10% to 90% of the nights) and red the 2026 setup. People who gave up are included.",
       x = NULL, y = "minutes") +
  theme(strip.text = element_text(size = rel(0.8)))
save_fig(p_wait, "04_wait_by_time.png", w = 11, h = 9)

# Where the plan adds the most sales.
het <- merge(cf[scenario == headline, .(draw, extra = d_beers_total)],
             post[, c("draw", prior_names), with = FALSE], by = "draw")
het_cols <- varying(het, prior_names)
Xh <- het[, lapply(.SD, function(v) z(as.numeric(v))), .SDcols = het_cols]
fit_h <- lm(as.formula(paste("extra ~", rhs(het_cols))), data = cbind(Xh, extra = het$extra))
hett <- coef_table(fit_h)
hett[, term := lab(term)]
fwrite(hett, file.path(tab_dir, "heterogeneous_effects.csv"))
p_het <- ggplot(hett, aes(estimate, reorder(term, estimate))) +
  geom_vline(xintercept = 0, colour = grey) +
  geom_errorbar(aes(xmin = lo, xmax = hi), orientation = "y", width = 0, colour = blue, linewidth = 1) +
  geom_point(colour = blue, size = 2.6) +
  labs(title = "In which nights the plan adds the most sales",
       subtitle = sprintf("Extra beers (plan minus 2026, same night) regressed on the unknowns.\nEffect of +1 standard deviation with 95%% CI. R² = %.2f.",
                          summary(fit_h)$r.squared),
       x = "extra beers per +1 SD", y = NULL)
save_fig(p_het, "06_heterogeneous_effects.png", w = 10, h = 6)

# What-if conditions.
wi_keys <- c("baseline", headline, labels[family == "what_if", scenario])
# A night meets the service target of config/staffing.yaml when both conditions hold.
tgt <- stf_cfg$service_target
wi <- met[scenario %in% wi_keys, {
  ok <- evening_p90_min <= tgt$evening_p90_min & abandon_share <= tgt$abandon_share
  ex <- exact_ci(sum(ok), .N)
  .(p90 = median(evening_p90_min), p90_lo = quantile(evening_p90_min, 0.05),
    p90_hi = quantile(evening_p90_min, 0.95), beers = median(beers_total),
    abandon = median(abandon_share), nights_met = sum(ok), nights = .N,
    met_lo = ex[1], met_hi = ex[2])
}, by = scenario]
wi[, label := lab_of[scenario]]
wi[, is_2026 := grepl("^baseline", scenario)]
fwrite(wi, file.path(tab_dir, "what_if.csv"))
p_wi <- ggplot(wi, aes(y = reorder(wrap(label, 36), p90))) +
  geom_errorbar(aes(xmin = p90_lo, xmax = p90_hi, colour = is_2026), orientation = "y", width = 0,
                 linewidth = 1.2, alpha = 0.6) +
  geom_point(aes(x = p90, colour = is_2026), size = 3.5) +
  scale_colour_manual(values = c(`TRUE` = red, `FALSE` = bronze), guide = "none") +
  labs(title = "If the night is different",
       subtitle = sprintf("Wait of 1 in 10 buyers, %s.\nDots are the median night and bars span 5%% to 95%% of the nights.", svc_window),
       x = "minutes", y = NULL)
save_fig(p_wi, "08_what_if.png", w = 10, h = 5.5)

# -----------------------------------------------------------------------------------------
# 3. Time-series models
# -----------------------------------------------------------------------------------------

# Event study: people in lines around the end of each set after 18:00.
ev <- rbindlist(lapply(sched$end, function(s0) {
  ser[scenario %in% c("baseline", headline) & clock_min >= s0 - 30 & clock_min <= s0 + 45,
      .(scenario, draw, rel = clock_min - s0, in_lines_total, start = s0)]
}))
ev <- ev[start >= 18 * 60]
ev_s <- ev[, .(med = median(in_lines_total), lo = quantile(in_lines_total, 0.1),
               hi = quantile(in_lines_total, 0.9)), by = .(scenario, rel)]
ev_s[, label := factor(lab_of[scenario], levels = lab_of[c("baseline", headline)])]
p_ev <- ggplot(ev_s, aes(rel, med, colour = label, fill = label)) +
  annotate("rect", xmin = 0, xmax = 25, ymin = -Inf, ymax = Inf, fill = blue, alpha = 0.1) +
  geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.15, colour = NA) +
  geom_line(linewidth = 1) +
  geom_vline(xintercept = 0, linetype = 2, colour = grey) +
  scale_colour_manual(NULL, values = c(red, bronze)) +
  scale_fill_manual(NULL, values = c(red, bronze)) +
  labs(title = "Lines around the end of a set (sets ending after 18:00)",
       subtitle = "Minute 0 is the end of a set. The shaded span is a typical changeover.",
       x = "minutes from the end of the set", y = "people in lines")

# Regression with AR(1) errors: beers sold per 5 min on people inside and changeover.
in_changeover <- function(m) !vapply(m, function(x) any(x >= sched$start & x < sched$end),
                                     logical(1))  # DJ sets between bands count as changeovers
ts_dat <- ser[scenario %in% c("baseline", headline) & clock_min >= 18 * 60 &
                clock_min <= 26 * 60]
setorder(ts_dat, scenario, draw, clock_min)
ts_dat[, sales := c(NA, diff(beers_total)), by = .(scenario, draw)]
ts_dat[, changeover := as.integer(in_changeover(clock_min))]
ts_dat[, occ100 := occupancy / 100]
arimax <- ts_dat[!is.na(sales), {
  f <- tryCatch(arima(sales, order = c(1, 0, 0), xreg = cbind(occ100, changeover)),
                error = function(e) NULL)
  if (is.null(f)) NULL else
    data.table(term = c("per 100 people inside", "during a changeover"),
               estimate = unname(coef(f)[c("occ100", "changeover")]),
               ar1 = unname(coef(f)["ar1"]),
               ljung_p = Box.test(residuals(f), lag = 6, type = "Ljung-Box", fitdf = 1)$p.value)
}, by = .(scenario, draw)]
arimax_s <- arimax[, .(med = median(estimate), lo = quantile(estimate, 0.1),
                       hi = quantile(estimate, 0.9), ar1 = median(ar1),
                       resid_ok = mean(ljung_p > 0.05)), by = .(scenario, term)]
arimax_s[, label := factor(lab_of[scenario], levels = lab_of[c("baseline", headline)])]
fwrite(arimax_s, file.path(tab_dir, "arimax_sales.csv"))
p_ar <- ggplot(arimax_s, aes(med, wrap(as.character(label), 28), colour = label)) +
  geom_vline(xintercept = 0, colour = grey) +
  geom_errorbar(aes(xmin = lo, xmax = hi), orientation = "y", width = 0, linewidth = 1.2) +
  geom_point(size = 3) +
  facet_wrap(~term, scales = "free_x") +
  scale_colour_manual(values = c(red, bronze), guide = "none") +
  labs(title = "Sales per 5 minutes, regression with AR(1) errors, 18:00–02:00",
       subtitle = "A bar whose sales do not follow the crowd is at its limit.\nDots are median coefficients across nights and bars span 10% to 90%.",
       x = "beers per 5 min", y = NULL)
save_fig(p_ev / p_ar + plot_layout(heights = c(1.4, 1)), "09_time_series_models.png",
         w = 11, h = 10)

# -----------------------------------------------------------------------------------------
# 4. Staffing reliability and capacity (tables written by scripts/run_staffing.py)
# -----------------------------------------------------------------------------------------

rel  <- fread(file.path(tab_dir, "staffing_reliability.csv"))
plan <- fread(file.path(tab_dir, "staffing_plan.csv"))
grid_levels <- stf_cfg$grid$crowd.n_total
g <- rel[n_total %in% grid_levels]
g[, att := factor(sprintf("%s tickets", comma(n_total)),
                  levels = sprintf("%s tickets", comma(sort(unique(n_total)))))]
plan_cells <- merge(g, unique(plan[, .(n_total, n_pour, sellers, level)]),
                    by = c("n_total", "n_pour", "sellers"))
p_g <- ggplot(g, aes(factor(n_pour), factor(sellers), fill = share_met)) +
  geom_tile(colour = paper, linewidth = 1) +
  geom_tile(data = plan_cells[level == "minimum"], fill = NA, colour = ink, linewidth = 1.2,
            linetype = 2) +
  geom_tile(data = plan_cells[level == "recommended"], fill = NA, colour = ink, linewidth = 1.6) +
  geom_text(aes(label = sprintf("%d/%d", nights_met, nights)), size = 4.2,
            colour = ifelse(g$share_met > 0.55, paper, ink)) +
  facet_wrap(~att, nrow = 1) +
  scale_fill_gradientn("share of nights", colours = c("#2b211f", "#5b2228", "#8c6a2c", bronze, "#e8c56a"),
                       limits = c(0, 1), labels = percent) +
  labs(title = "In how many nights each crew meets the waiting target",
       subtitle = sprintf("The target is that 9 of 10 buyers wait at most %s min (%s) and at most %s%% of attempts are abandoned.\nSolid outline: recommended crew, the fewest staff hours that meets it in at least %s%% of the nights.\nDashed outline: minimum crew, the same for %s%% of the nights.",
                          stf_cfg$service_target$evening_p90_min, svc_window,
                          100 * stf_cfg$service_target$abandon_share,
                          100 * stf_cfg$reliability_recommended, 100 * stf_cfg$reliability),
       x = "serving stations at the bar", y = "roaming sellers") +
  theme(panel.grid = element_blank(), legend.key.width = unit(1.6, "cm"))
save_fig(p_g, "12_staffing_reliability.png", w = 12, h = 6.2)

lim <- stf_cfg$safety$floor_density_limit
cap <- rel[, .(density = median(floor_density), d_lo = min(floor_density_lo),
               d_hi = max(floor_density_hi), occ = median(inside_peak)), by = n_total]
setorder(cap, n_total)
fwrite(cap, file.path(tab_dir, "capacity.csv"))
p_cap <- ggplot(cap, aes(n_total, density)) +
  geom_hline(yintercept = lim, linetype = 2, colour = red) +
  annotate("text", x = min(cap$n_total), y = lim, vjust = -0.6, hjust = 0, size = 4,
           colour = red, label = sprintf("NFPA 101 limit for assembly areas, %.1f people/m²", lim)) +
  geom_ribbon(aes(ymin = d_lo, ymax = d_hi), fill = bronze, alpha = 0.2) +
  geom_line(colour = bronze, linewidth = 1) +
  geom_point(colour = bronze, size = 3) +
  geom_text(aes(label = sprintf("%s inside", comma(round(occ)))), vjust = 2.2, size = 4,
            colour = ink) +
  scale_x_continuous(breaks = cap$n_total, labels = comma, expand = expansion(mult = 0.1)) +
  scale_y_continuous(expand = expansion(c(0.2, 0.15))) +
  labs(title = "People per m² of free floor at the fullest moment",
       subtitle = "People standing on the free floor (audience area without vendor strips and tables), divided by its area.\nLabels give everyone inside at that moment.",
       x = "tickets sold", y = "people per m²")
save_fig(p_cap, "13_capacity.png", w = 10, h = 5.6)

# ---- 14 Bar workers: busy share by hour and seller time ------------------------------
# bar_busy_hHH is the busy share of the bar workers on shift in clock hour HH (13 to 26 for
# 13:00 to 02:00); seller_*_share is the share of seller time in each state.
busy_cols <- grep("^bar_busy_h[0-9]+$", names(met), value = TRUE)
if (length(busy_cols)) {
  wk <- melt(met[scenario %in% c("baseline", headline), c("scenario", "draw", busy_cols),
                 with = FALSE],
             id.vars = c("scenario", "draw"), variable.name = "hour", value.name = "busy")
  wk[, hour := as.integer(sub("bar_busy_h", "", hour))]
  wk <- wk[!is.na(busy) & hour <= 26]
  wk_sum <- wk[, .(med = median(busy), lo = quantile(busy, 0.05), hi = quantile(busy, 0.95),
                   nights = .N), by = .(scenario, hour)]
  wk_sum[, setup := factor(ifelse(scenario == "baseline", "2026 setup", "Plan"),
                           levels = c("2026 setup", "Plan"))]
  fwrite(wk_sum[order(scenario, hour)], file.path(tab_dir, "worker_busy.csv"))
  p_busy <- ggplot(wk_sum, aes(hour, med, colour = setup, fill = setup)) +
    geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.2, colour = NA) +
    geom_line(linewidth = 1) + geom_point(size = 2) +
    scale_colour_manual(values = c("2026 setup" = red, "Plan" = bronze), name = NULL) +
    scale_fill_manual(values = c("2026 setup" = red, "Plan" = bronze), name = NULL) +
    scale_x_continuous(breaks = seq(13, 26, 2), labels = sprintf("%02d:00", seq(13, 26, 2) %% 24)) +
    scale_y_continuous(labels = percent, limits = c(0, 1)) +
    labs(title = "Share of time the bar workers on shift are busy",
         subtitle = "Median night and 5% to 95% of nights. Charging and pouring both count as busy.",
         x = "clock hour", y = "busy share")
  sel_cols <- c(walking = "seller_walking_share", selling = "seller_selling_share",
                `to refill` = "seller_to_refill_share", refilling = "seller_refilling_share")
  sel <- melt(met[scenario == headline, c("draw", sel_cols), with = FALSE], id.vars = "draw",
              variable.name = "state", value.name = "share")
  sel[, state := factor(names(sel_cols)[match(state, sel_cols)], levels = names(sel_cols))]
  sel_sum <- sel[, .(med = median(share), lo = quantile(share, 0.05),
                     hi = quantile(share, 0.95)), by = state]
  ch <- met[scenario %in% c("baseline", headline),
            .(charging = median(bar_charging_share), charging_lo = quantile(bar_charging_share, 0.05),
              charging_hi = quantile(bar_charging_share, 0.95), busy = median(bar_busy_share),
              busy_lo = quantile(bar_busy_share, 0.05), busy_hi = quantile(bar_busy_share, 0.95)),
            by = scenario]
  fwrite(rbind(sel_sum[, .(scenario = headline, quantity = paste("seller", state), med, lo, hi)],
               ch[, .(scenario, quantity = "bar charging share of busy time", med = charging,
                      lo = charging_lo, hi = charging_hi)],
               ch[, .(scenario, quantity = "bar busy share, whole night", med = busy,
                      lo = busy_lo, hi = busy_hi)]),
         file.path(tab_dir, "worker_shares.csv"))
  p_sel <- ggplot(sel_sum, aes(med, state)) +
    geom_errorbar(aes(xmin = lo, xmax = hi), orientation = "y", width = 0, colour = muted) +
    geom_point(size = 3, colour = bronze) +
    scale_x_continuous(labels = percent, limits = c(0, 1)) +
    labs(title = "Seller time under the plan", subtitle = "Median night and 5% to 95% of nights",
         x = "share of time on shift", y = NULL)
  save_fig(p_busy / p_sel + plot_layout(heights = c(2, 1)), "14_bar_workers.png", w = 10, h = 8)
}

writeLines(capture.output(sessionInfo()), file.path(tab_dir, "sessionInfo.txt"))
cat("figures written to", fig_dir, "\n")
