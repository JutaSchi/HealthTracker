#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>

#include <zephyr/sys/printk.h>
#include <string.h>

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME

#define BT_UUID_HEALTHTRACKER_SERVICE_VAL \
    BT_UUID_128_ENCODE(0x7b5e0001, 0x9b2a, 0x4c7a, 0x8f5e, 0x4d2c6a110001)

#define BT_UUID_HEALTHTRACKER_STATUS_VAL \
    BT_UUID_128_ENCODE(0x7b5e0002, 0x9b2a, 0x4c7a, 0x8f5e, 0x4d2c6a110001)

static struct bt_uuid_128 healthtracker_service_uuid =
    BT_UUID_INIT_128(BT_UUID_HEALTHTRACKER_SERVICE_VAL);

static struct bt_uuid_128 healthtracker_status_uuid =
    BT_UUID_INIT_128(BT_UUID_HEALTHTRACKER_STATUS_VAL);


/* -------------------------------------------------------
 * MAX30102
 * ------------------------------------------------------- */

#define MAX30102_NODE DT_NODELABEL(max30102)

#if !DT_NODE_EXISTS(MAX30102_NODE)
#error "MAX30102 devicetree node not found"
#endif

static const struct device *max30102 =
    DEVICE_DT_GET(MAX30102_NODE);


/* -------------------------------------------------------
 * BLE state
 * ------------------------------------------------------- */

static bool connected;
static bool notifications_enabled;

static char status_message[128] = "HealthTracker ready";


static ssize_t read_status(struct bt_conn *conn,
                           const struct bt_gatt_attr *attr,
                           void *buf,
                           uint16_t len,
                           uint16_t offset)
{
    const char *value = attr->user_data;

    return bt_gatt_attr_read(conn,
                             attr,
                             buf,
                             len,
                             offset,
                             value,
                             strlen(value));
}


static void status_ccc_changed(const struct bt_gatt_attr *attr,
                               uint16_t value)
{
    ARG_UNUSED(attr);

    notifications_enabled =
        (value == BT_GATT_CCC_NOTIFY);

    printk("Status notifications %s\n",
           notifications_enabled ? "enabled" : "disabled");
}


/* -------------------------------------------------------
 * BLE GATT service
 * ------------------------------------------------------- */

BT_GATT_SERVICE_DEFINE(healthtracker_service,

    BT_GATT_PRIMARY_SERVICE(&healthtracker_service_uuid),

    BT_GATT_CHARACTERISTIC(
        &healthtracker_status_uuid.uuid,

        BT_GATT_CHRC_READ |
        BT_GATT_CHRC_NOTIFY,

        BT_GATT_PERM_READ,

        read_status,
        NULL,
        status_message
    ),

    BT_GATT_CCC(
        status_ccc_changed,
        BT_GATT_PERM_READ |
        BT_GATT_PERM_WRITE
    )
);


/* -------------------------------------------------------
 * BLE connection callbacks
 * ------------------------------------------------------- */

static void on_connected(struct bt_conn *conn,
                         uint8_t err)
{
    ARG_UNUSED(conn);

    if (err != 0) {
        printk("Connection failed (err %u)\n", err);
        return;
    }

    connected = true;

    printk("PC connected\n");
}


static void on_disconnected(struct bt_conn *conn,
                            uint8_t reason)
{
    ARG_UNUSED(conn);

    connected = false;
    notifications_enabled = false;

    printk("PC disconnected (reason %u); advertising again\n",
           reason);
}


BT_CONN_CB_DEFINE(connection_callbacks) = {
    .connected = on_connected,
    .disconnected = on_disconnected,
};


/* -------------------------------------------------------
 * Sensor + BLE worker
 * ------------------------------------------------------- */

static void status_work_handler(struct k_work *work);

K_WORK_DELAYABLE_DEFINE(status_work,
                         status_work_handler);


static void status_work_handler(struct k_work *work)
{
    ARG_UNUSED(work);

    struct sensor_value red;
    struct sensor_value ir;

    int err;

    /*
     * Read a fresh sample from MAX30102.
     */
    err = sensor_sample_fetch(max30102);

    if (err != 0) {
        printk("MAX30102 sample fetch failed: %d\n", err);
        goto schedule_next;
    }

    /*
     * Get RED LED channel.
     */
    err = sensor_channel_get(max30102,
                             SENSOR_CHAN_RED,
                             &red);

    if (err != 0) {
        printk("Failed to read RED: %d\n", err);
        goto schedule_next;
    }

    /*
     * Get IR LED channel.
     */
    err = sensor_channel_get(max30102,
                             SENSOR_CHAN_IR,
                             &ir);

    if (err != 0) {
        printk("Failed to read IR: %d\n", err);
        goto schedule_next;
    }

    /*
     * Print locally too, which makes debugging
     * considerably less painful.
     */
    printk("MAX30102: RED=%d.%06d IR=%d.%06d\n",
           red.val1,
           red.val2,
           ir.val1,
           ir.val2);


    /*
     * Send over BLE if the phone/PC subscribed.
     */
    if (connected && notifications_enabled) {

        int len = snprintk(
            status_message,
            sizeof(status_message),

            "red=%d.%06d,ir=%d.%06d",

            red.val1,
            red.val2,

            ir.val1,
            ir.val2
        );

        err = bt_gatt_notify(
            NULL,
            &healthtracker_service.attrs[2],
            status_message,
            len
        );

        if (err != 0) {
            printk("BLE notification failed: %d\n", err);
        }
    }


schedule_next:

    /*
     * 10 Hz update rate.
     *
     * 100 ms = 10 readings/sec
     */
    k_work_schedule(&status_work,
                    K_MSEC(100));
}


/* -------------------------------------------------------
 * BLE advertising
 * ------------------------------------------------------- */

static const struct bt_data advertising_data[] = {
    BT_DATA_BYTES(
        BT_DATA_FLAGS,
        BT_LE_AD_GENERAL |
        BT_LE_AD_NO_BREDR
    ),

    BT_DATA_BYTES(
        BT_DATA_UUID128_ALL,
        BT_UUID_HEALTHTRACKER_SERVICE_VAL
    ),
};


static const struct bt_data scan_response_data[] = {
    BT_DATA(
        BT_DATA_NAME_COMPLETE,
        DEVICE_NAME,
        sizeof(DEVICE_NAME) - 1
    ),
};


/* -------------------------------------------------------
 * Main
 * ------------------------------------------------------- */

int main(void)
{
    int err;

    printk("\n");
    printk("=================================\n");
    printk(" HealthTracker\n");
    printk(" nRF54L15 + MAX30102\n");
    printk("=================================\n");


    /* ---------------------------------------------------
     * Check MAX30102
     * --------------------------------------------------- */

    if (!device_is_ready(max30102)) {
        printk("ERROR: MAX30102 is not ready\n");
        printk("Check I2C wiring and devicetree.\n");

        return -ENODEV;
    }

    printk("MAX30102 detected\n");


    /* ---------------------------------------------------
     * Bluetooth
     * --------------------------------------------------- */

    err = bt_enable(NULL);

    if (err) {
        printk("Bluetooth init failed (err %d)\n",
               err);

        return err;
    }

    printk("Bluetooth initialized\n");


    /* ---------------------------------------------------
     * Start advertising
     * --------------------------------------------------- */

    err = bt_le_adv_start(
        BT_LE_ADV_CONN_FAST_1,

        advertising_data,
        ARRAY_SIZE(advertising_data),

        scan_response_data,
        ARRAY_SIZE(scan_response_data)
    );

    if (err) {
        printk("Advertising failed (err %d)\n",
               err);

        return err;
    }

    printk("Advertising as %s\n",
           DEVICE_NAME);

    printk("Waiting for BLE connection...\n");


    /* ---------------------------------------------------
     * Start sensor worker
     * --------------------------------------------------- */

    k_work_schedule(
        &status_work,
        K_MSEC(100)
    );


    while (1) {
        k_sleep(K_SECONDS(1));
    }

    return 0;
}