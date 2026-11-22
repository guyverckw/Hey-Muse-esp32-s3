/*
 * Waveshare ESP32-S3-Touch-LCD-1.85 (Rev 2.1 hardware tested).
 * Initial Muse port: LCD and touch only. Voice and audio intentionally off.
 * Vendor LCD controller reference: waveshareteam/ESP32-S3-Touch-LCD-1.85
 */
#include <string.h>

#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/ledc.h"
#include "driver/spi_master.h"
#include "esp_check.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_log.h"
#include "esp_lv_adapter.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "muse_board.h"
#include "muse_lcd_bands.h"
#include "muse_mem.h"
#include "esp_lcd_st77916.h"
#include "muse_185_lcd_case2.h"

static const char *TAG = "muse_185";

#define LCD_RES           360
#define LCD_HOST          SPI2_HOST
#define LCD_CLK           GPIO_NUM_40
#define LCD_CS            GPIO_NUM_21
#define LCD_D0            GPIO_NUM_46
#define LCD_D1            GPIO_NUM_45
#define LCD_D2            GPIO_NUM_42
#define LCD_D3            GPIO_NUM_41
#define LCD_BL            GPIO_NUM_5
#define EXIO_ADDR         0x20
#define EXIO_OUTPUT_REG   0x01
#define EXIO_CONFIG_REG   0x03
#define EXIO_TOUCH_RST    BIT(0)
#define EXIO_LCD_RST      BIT(1)
#define TOUCH_ADDR        0x15
#define TOUCH_POINTS_REG  0x02
#define TOUCH_AUTOSLEEP   0xFE
#define LCD_CHUNK_BYTES   (LCD_RES * 8 * 2)
#define DRAW_BUF_LINES    90

static i2c_master_bus_handle_t s_periph_bus, s_touch_bus;
static i2c_master_dev_handle_t s_expander, s_touch_dev;
static esp_lcd_panel_io_handle_t s_lcd_io;
static esp_lcd_panel_handle_t s_lcd_panel;
static muse_gpio_button_t s_boot;

static esp_err_t add_i2c(i2c_master_bus_handle_t bus, uint8_t addr, i2c_master_dev_handle_t *dev)
{
    const i2c_device_config_t cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = addr,
        .scl_speed_hz = addr == TOUCH_ADDR ? 400000 : 100000,
    };
    return i2c_master_bus_add_device(bus, &cfg, dev);
}

static esp_err_t reg_read(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t *data, size_t n)
{
    return i2c_master_transmit_receive(dev, &reg, 1, data, n, 100);
}

static esp_err_t reg_write(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t value)
{
    uint8_t tx[] = { reg, value };
    return i2c_master_transmit(dev, tx, sizeof(tx), 100);
}

/* Preserve all expander output bits except reset pins. */
static esp_err_t exio_reset(uint8_t mask)
{
    uint8_t v;
    ESP_RETURN_ON_ERROR(reg_read(s_expander, EXIO_OUTPUT_REG, &v, 1), TAG, "exio read");
    ESP_RETURN_ON_ERROR(reg_write(s_expander, EXIO_OUTPUT_REG, v & ~mask), TAG, "exio reset low");
    vTaskDelay(pdMS_TO_TICKS(10));
    ESP_RETURN_ON_ERROR(reg_write(s_expander, EXIO_OUTPUT_REG, v | mask), TAG, "exio reset high");
    vTaskDelay(pdMS_TO_TICKS(50));
    return ESP_OK;
}

static esp_err_t init(void)
{
    const i2c_master_bus_config_t peripheral = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = GPIO_NUM_11,
        .scl_io_num = GPIO_NUM_10,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    const i2c_master_bus_config_t touch_bus = {
        .i2c_port = I2C_NUM_1,
        .sda_io_num = GPIO_NUM_1,
        .scl_io_num = GPIO_NUM_3,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    ESP_RETURN_ON_ERROR(i2c_new_master_bus(&peripheral, &s_periph_bus), TAG, "peripheral i2c");
    ESP_RETURN_ON_ERROR(add_i2c(s_periph_bus, EXIO_ADDR, &s_expander), TAG, "TCA9554");
    ESP_RETURN_ON_ERROR(i2c_new_master_bus(&touch_bus, &s_touch_bus), TAG, "touch i2c");
    ESP_RETURN_ON_ERROR(add_i2c(s_touch_bus, TOUCH_ADDR, &s_touch_dev), TAG, "CST816");

    /* Waveshare initializes all eight TCA9554 channels as outputs. */
    ESP_RETURN_ON_ERROR(reg_write(s_expander, EXIO_CONFIG_REG, 0), TAG, "expander outputs");
    ESP_RETURN_ON_ERROR(exio_reset(EXIO_LCD_RST | EXIO_TOUCH_RST), TAG, "LCD/touch reset");
    ESP_RETURN_ON_ERROR(reg_write(s_touch_dev, TOUCH_AUTOSLEEP, 1), TAG, "touch auto-sleep off");

    ESP_RETURN_ON_ERROR(muse_gpio_button_init(&s_boot, GPIO_NUM_0), TAG, "BOOT button");
    s_boot.pressed = gpio_get_level(GPIO_NUM_0) == 0;
    return ESP_OK;
}

/* CST816 uses one finger: count at 0x02, x and y packed in 12 bits. */
static void touch_read(lv_indev_t *indev, lv_indev_data_t *data)
{
    (void)indev;
    uint8_t pt[5] = { 0 };
    if (reg_read(s_touch_dev, TOUCH_POINTS_REG, pt, sizeof(pt)) != ESP_OK || pt[0] == 0) {
        data->state = LV_INDEV_STATE_RELEASED;
        return;
    }
    int x = ((pt[1] & 0x0f) << 8) | pt[2];
    int y = ((pt[3] & 0x0f) << 8) | pt[4];
    data->point.x = x < LCD_RES ? x : LCD_RES - 1;
    data->point.y = y < LCD_RES ? y : LCD_RES - 1;
    data->state = LV_INDEV_STATE_PRESSED;
}

static lv_display_t *display_start(lv_indev_t **touch)
{
    /* Must be created on Muse's display core, as its band sender is. */
    const spi_bus_config_t bus = ST77916_PANEL_BUS_QSPI_CONFIG(
        LCD_CLK, LCD_D0, LCD_D1, LCD_D2, LCD_D3, LCD_CHUNK_BYTES);
    ESP_RETURN_ON_FALSE(spi_bus_initialize(LCD_HOST, &bus, SPI_DMA_CH_AUTO) == ESP_OK,
                        NULL, TAG, "QSPI bus");

    /* The working Waveshare demo probes register 0x04 at 3 MHz to choose
     * between two LCD subtypes. This physical board returned 00 02 7f 7f. */
    esp_lcd_panel_io_spi_config_t io_cfg = ST77916_PANEL_IO_QSPI_CONFIG(LCD_CS, NULL, NULL);
    io_cfg.pclk_hz = 3000000;
    ESP_RETURN_ON_FALSE(esp_lcd_new_panel_io_spi(LCD_HOST, &io_cfg, &s_lcd_io) == ESP_OK,
                        NULL, TAG, "LCD probe io");
    uint8_t chip_id[4] = { 0 };
    const uint32_t read_cmd = (0x0bUL << 24) | (0x04UL << 8);
    esp_err_t err = esp_lcd_panel_io_rx_param(s_lcd_io, read_cmd, chip_id, sizeof(chip_id));
    ESP_RETURN_ON_FALSE(err == ESP_OK, NULL, TAG, "LCD register read");
    ESP_LOGI(TAG, "ST77916 register 04: %02x %02x %02x %02x",
             chip_id[0], chip_id[1], chip_id[2], chip_id[3]);
    ESP_RETURN_ON_FALSE(chip_id[0] == 0 && chip_id[1] == 2 && chip_id[2] == 0x7f &&
                        chip_id[3] == 0x7f, NULL, TAG, "unsupported LCD subtype; not guessing init");

    ESP_RETURN_ON_FALSE(esp_lcd_panel_io_del(s_lcd_io) == ESP_OK, NULL, TAG, "probe cleanup");
    s_lcd_io = NULL;
    io_cfg.pclk_hz = 80000000;  /* Waveshare's tested QSPI clock */
    ESP_RETURN_ON_FALSE(esp_lcd_new_panel_io_spi(LCD_HOST, &io_cfg, &s_lcd_io) == ESP_OK,
                        NULL, TAG, "LCD io");

    st77916_vendor_config_t vendor = {
        .init_cmds = muse_185_case2_init,
        .init_cmds_size = sizeof(muse_185_case2_init) / sizeof(muse_185_case2_init[0]),
        .flags.use_qspi_interface = 1,
    };
    const esp_lcd_panel_dev_config_t cfg = {
        .reset_gpio_num = GPIO_NUM_NC, /* EXIO2 reset has already been pulsed */
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB,
        .bits_per_pixel = 16,
        .vendor_config = &vendor,
    };
    ESP_RETURN_ON_FALSE(esp_lcd_new_panel_st77916(s_lcd_io, &cfg, &s_lcd_panel) == ESP_OK,
                        NULL, TAG, "ST77916 panel");
    ESP_RETURN_ON_FALSE(esp_lcd_panel_reset(s_lcd_panel) == ESP_OK, NULL, TAG, "panel reset");
    ESP_RETURN_ON_FALSE(esp_lcd_panel_init(s_lcd_panel) == ESP_OK, NULL, TAG, "panel init");
    ESP_RETURN_ON_FALSE(esp_lcd_panel_disp_on_off(s_lcd_panel, true) == ESP_OK,
                        NULL, TAG, "panel on");

    const ledc_timer_config_t timer = {
        .speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_13_BIT,
        .timer_num = LEDC_TIMER_0, .freq_hz = 5000, .clk_cfg = LEDC_AUTO_CLK,
    };
    const ledc_channel_config_t channel = {
        .gpio_num = LCD_BL, .speed_mode = LEDC_LOW_SPEED_MODE, .channel = LEDC_CHANNEL_0,
        .intr_type = LEDC_INTR_DISABLE, .timer_sel = LEDC_TIMER_0, .duty = 4096,
    };
    ESP_RETURN_ON_FALSE(ledc_timer_config(&timer) == ESP_OK, NULL, TAG, "backlight timer");
    ESP_RETURN_ON_FALSE(ledc_channel_config(&channel) == ESP_OK, NULL, TAG, "backlight PWM");

    esp_lv_adapter_config_t adapter_cfg = ESP_LV_ADAPTER_DEFAULT_CONFIG();
    adapter_cfg.task_core_id = MUSE_UI_CORE;
    adapter_cfg.task_priority = MUSE_UI_PRIORITY;
    ESP_RETURN_ON_FALSE(esp_lv_adapter_init(&adapter_cfg) == ESP_OK, NULL, TAG, "LVGL adapter");
    const esp_lv_adapter_display_config_t disp_cfg = {
        .panel = s_lcd_panel,
        .panel_io = s_lcd_io,
        .profile = {
            .interface = ESP_LV_ADAPTER_PANEL_IF_OTHER,
            .rotation = ESP_LV_ADAPTER_ROTATE_0,
            .hor_res = LCD_RES,
            .ver_res = LCD_RES,
        },
        .tear_avoid_mode = ESP_LV_ADAPTER_TEAR_AVOID_MODE_NONE,
    };
    lv_display_t *display = muse_lcd_bands_register(disp_cfg, DRAW_BUF_LINES, LCD_CHUNK_BYTES);
    ESP_RETURN_ON_FALSE(display != NULL, NULL, TAG, "LVGL display bands");

    *touch = lv_indev_create();
    ESP_RETURN_ON_FALSE(*touch != NULL, NULL, TAG, "LVGL touch input");
    lv_indev_set_type(*touch, LV_INDEV_TYPE_POINTER);
    lv_indev_set_display(*touch, display);
    lv_indev_set_read_cb(*touch, touch_read);
    ESP_RETURN_ON_FALSE(esp_lv_adapter_start() == ESP_OK, NULL, TAG, "LVGL start");
    ESP_LOGI(TAG, "1.85-inch LCD and touch started");
    return display;
}

static bool display_lock(int timeout_ms)
{
    return esp_lv_adapter_lock(timeout_ms) == ESP_OK;
}

static void set_brightness(int pct)
{
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    uint32_t duty = (uint32_t)pct * 8191 / 100;
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

static unsigned poll_buttons(void)
{
    /* Temporary BOOT control for UI testing; no voice until audio is ported. */
    return muse_gpio_button_poll(&s_boot);
}

static const muse_board_t s_board = {
    .name = "Waveshare ESP32-S3-Touch-LCD-1.85",
    .width = LCD_RES,
    .height = LCD_RES,
    .round = true,
    .touch = true,
    .diagonal_in = 1.85f,
    .talk_button = "boot",
    .aux_button = "none",
    .talk_hint = { LV_ALIGN_CENTER, 115, 100 },
    .frame_ms = 40,
    .init = init,
    .display_start = display_start,
    .display_lock = display_lock,
    .display_unlock = esp_lv_adapter_unlock,
    .set_brightness = set_brightness,
    .audio_init = NULL,     /* display-only milestone */
    .mic_slot = -1,
    .poll_buttons = poll_buttons,
    .read_power = NULL,
    .power_off = NULL,      /* until power circuitry is separately ported */
};

const muse_board_t *muse_board_get(void)
{
    return &s_board;
}
