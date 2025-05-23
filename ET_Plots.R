library(ggplot2)
library(ggrepel)
library(jpeg)
library(grid)
library(MASS)
library(dplyr)
library(tidyr)
library(grid)

# Clear environment
rm(list = ls())

# Turn off scientific notation
options(scipen = 999)

# Change wd
current_wd <- dirname(rstudioapi::getSourceEditorContext()$path)
setwd(current_wd)

# === Load data ===
df <- read.csv("gaze_nico_test_5.csv")

# === Extract image ON/OFF events ===
events <- df %>%
  filter(grepl("IMAGE", message)) %>%
  mutate(
    image = sub(".*IMAGE (.*\\.JPG) .*", "\\1", message),
    event = sub(".*(ON|OFF)", "\\1", message)
  ) %>%
  dplyr::select(timestamp, image, event)

# === Match ON/OFF for each image ===
image_events <- events %>%
  pivot_wider(names_from = event, values_from = timestamp)

# === Loop over each image ===
for (i in 1:nrow(image_events)) {
  img_file <- image_events$image[i]
  on_time <- image_events$ON[i]
  off_time <- image_events$OFF[i]
  
  # Load and fade image
  img <- readJPEG(img_file)
  h <- dim(img)[1]
  w <- dim(img)[2]
  fade_strength <- 0.25
  img_faded <- img * fade_strength + (1 - fade_strength)
  bg <- rasterGrob(img_faded, width = unit(1, "npc"), height = unit(1, "npc"),
                   interpolate = TRUE)
  
  # Filter gaze data
  df_seg <- df %>%
    filter(timestamp >= on_time, timestamp <= off_time,
           !is.na(x), !is.na(y), (x != 0 | y != 0)) %>%
    mutate(fix = as.logical(fix))
  
  fix <- df_seg %>%
    filter(fix) %>%
    mutate(fixation_number = row_number())
  
  # === Heatmap ===
  heatmap_plot <- ggplot(df_seg, aes(x = x, y = y)) +
    annotation_custom(bg, xmin = 0, xmax = w, ymin = 0, ymax = h) +
    stat_density_2d(aes(fill = ..level..), geom = "polygon", colour = NA, alpha = 0.6) +
    scale_fill_viridis_c() +
    coord_fixed(ratio = 1, xlim = c(0, w), ylim = c(h, 0)) +
    theme_void() +
    ggtitle(paste("Gaze Heatmap:", img_file))
  print(heatmap_plot)
  
  # === Fixation Plot ===
  fixation_plot <- ggplot(fix, aes(x = x, y = y)) +
    annotation_custom(bg, xmin = 0, xmax = w, ymin = 0, ymax = h) +
    geom_path(color = "grey30", linewidth = 0.7, lineend = "round") +  # connect fixations
    geom_point(color = "limegreen", size = 3) +
    geom_text_repel(aes(label = fixation_number), size = 2.5, color = "black") +
    coord_fixed(ratio = 1, xlim = c(0, w), ylim = c(h, 0)) +
    theme_void() +
    ggtitle(paste("Fixation Sequence:", img_file))
  print(fixation_plot)
}