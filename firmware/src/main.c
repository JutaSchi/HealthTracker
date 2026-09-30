#include <zephyr/kernel.h>
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

static bool connected;
static bool notifications_enabled;
static char status_message[64] = "HealthTracker ready";

static ssize_t read_status(struct bt_conn *conn,
                           const struct bt_gatt_attr *attr,
                           void *buf,
                           uint16_t len,
                           uint16_t offset)
{
    const char *value = attr->user_data;

    return bt_gatt_attr_read(conn, attr, buf, len, offset, value, strlen(value));
}

static void status_ccc_changed(const struct bt_gatt_attr *attr, uint16_t value)
{
    ARG_UNUSED(attr);
    notifications_enabled = (value == BT_GATT_CCC_NOTIFY);
    printk("Status notifications %s\n",
           notifications_enabled ? "enabled" : "disabled");
}

BT_GATT_SERVICE_DEFINE(healthtracker_service,
    BT_GATT_PRIMARY_SERVICE(&healthtracker_service_uuid),
    BT_GATT_CHARACTERISTIC(&healthtracker_status_uuid.uuid,
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           read_status, NULL, status_message),
    BT_GATT_CCC(status_ccc_changed, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE)
);

static void on_connected(struct bt_conn *conn, uint8_t err)
{
    ARG_UNUSED(conn);

    if (err != 0) {
        printk("Connection failed (err %u)\n", err);
        return;
    }

    connected = true;
    printk("PC connected\n");
}

static void on_disconnected(struct bt_conn *conn, uint8_t reason)
{
    ARG_UNUSED(conn);

    connected = false;
    notifications_enabled = false;
    printk("PC disconnected (reason %u); advertising again\n", reason);
}

BT_CONN_CB_DEFINE(connection_callbacks) = {
    .connected = on_connected,
    .disconnected = on_disconnected,
};

static void status_work_handler(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(status_work, status_work_handler);

static void status_work_handler(struct k_work *work)
{
    ARG_UNUSED(work);

    if (connected && notifications_enabled) {
        int len = snprintk(status_message, sizeof(status_message),
                           "uptime_s=%u",
                           (uint32_t)(k_uptime_get() / MSEC_PER_SEC));
        int err = bt_gatt_notify(NULL, &healthtracker_service.attrs[2],
                                 status_message, len);

        if (err != 0) {
            printk("Status notification failed (err %d)\n", err);
        }
    }

    k_work_schedule(&status_work, K_SECONDS(2));
}

static const struct bt_data advertising_data[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR),
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_HEALTHTRACKER_SERVICE_VAL),
};

static const struct bt_data scan_response_data[] = {
    BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, sizeof(DEVICE_NAME) - 1),
};

int main(void)
{
    int err;

    printk("Starting HealthTracker BLE peripheral...\n");

    err = bt_enable(NULL);
    if (err) {
        printk("Bluetooth init failed (err %d)\n", err);
        return err;
    }

    printk("Bluetooth initialized\n");
    err = bt_le_adv_start(BT_LE_ADV_CONN, advertising_data,
                          ARRAY_SIZE(advertising_data), scan_response_data,
                          ARRAY_SIZE(scan_response_data));
    if (err) {
        printk("Advertising failed to start (err %d)\n", err);
        return err;
    }

    printk("Advertising as %s; waiting for the PC app\n", DEVICE_NAME);
    k_work_schedule(&status_work, K_SECONDS(2));

    while (1) {
        k_sleep(K_SECONDS(1));
    }

}