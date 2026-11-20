# Extension Data

Plugins add their own data to CoCart responses under `extensions`: on the cart, on each cart item, and on products. This page lists what CoCart Plus sends for the plugins it supports, and how to send the customer's choices back.

## Plugins CoCart Plus supports

CoCart Plus adds the data for the plugins it supports, and only where it applies: subscription details appear on a subscription product, bundle details on a bundle in the cart, and so on.

| Plugin | Cart | Cart item | Product |
| --- | --- | --- | --- |
| WooCommerce Subscriptions, Storewide plans, Milo Subscriptions | `recurring_totals` | `subscription_data` | `subscription_data` |
| Subscription plans: WooCommerce Subscriptions 9+ or All Products for WooCommerce Subscriptions | `recurring_totals` | `subscription_schemes` | `subscription_schemes` |
| Gifting for WooCommerce Subscriptions | | `gift_recipient` | `gifting` |
| WooCommerce Bookings | | `booking_data` | `booking_data` |
| Accommodation Bookings | | `accommodation_booking_data` | `accommodation_booking_data` |
| Composite Products | | `composite_data` | `composite_data` |
| Product Bundles | | `bundle_data` | `bundle_data` |
| Product Add-Ons | | `addons` | `addons` |
| Discount Rules (Flycart) | | `discount` | `discount` |
| Advanced Dynamic Pricing (AlgolPlus) | | `adp` | |
| WooCommerce Warranty | | `warranty` | `warranty` |
| Points and Rewards | `points_and_rewards` | | `points_and_rewards` |
| MSRP Pricing | | | `msrp_data` |
| Min/Max Quantities | | | `quantity_rules` |
| Dokan | | | `vendor` |
| Product Condition | | | `condition` |

Every key is optional, since a plugin's data is only there when the plugin is active and it applies. With none, `extensions` is empty (`{}` from CoCart Starter 5, `[]` from CoCart 4.x; `get_extensions()` returns `{}` for both).

Amounts are minor-unit strings, like the rest of CoCart (`"1800"` for 18.00). The amounts in `recurring_totals` follow the cart's `formatted` option, like the cart's own totals.

```python
response = client.cart().get()

for item in response.get_items():
    subscription = item["extensions"].get("subscription_data")
    if subscription:
        print(subscription["price_string"], subscription["first_renewal"]["html"])

# One entry per recurring cart, keyed by the subscription's item key.
recurring = response.get_extensions().get("recurring_totals", {})
```

## Shapes

### Subscriptions

`subscription_data` (product and cart item):

| Field | Type | Notes |
| --- | --- | --- |
| `billing_period` | array | `interval`, `period`, `length`, `trial_period`, `trial_length`, `trial_expiration_date`, `expiration_date`. The dates are `Y-m-d H:i:s` (GMT) for a subscription started now, or `0` for no trial / never expires |
| `sign_up_fee` | string | Minor units |
| `pay_now` | string | What is paid at checkout: the sign-up fee alone during a trial or before a synchronised renewal day, the prorated price plus the sign-up fee when the store prorates, otherwise the price plus the sign-up fee |
| `needs_one_time_shipping` | bool | |
| `price_string` | string | Ready to display |
| `first_renewal` | array | `date` (`Y-m-d H:i:s` GMT, or `0` with no renewal), `timestamp` (int), `html` ("First renewal: …") |

`subscription_schemes` (product and cart item) is a list of options, listed only when there's a choice to make (a one-time option, or more than one plan):

| Field | Type | Notes |
| --- | --- | --- |
| `price` | string | Minor units |
| `period` | string | e.g. `/ month` |
| `value` | string | Send as `convert_to_sub`; `"0"` is one-time |
| `rest_url` | string | Ready-made request: on a product it adds it to the cart with this option, on a cart item it switches to it |
| `selected` | bool | Cart items only: the option the item has now |

`recurring_totals` (cart) is keyed by the subscription's item key. Each entry has `totals` (`period`, `subtotal`, `total`, `label`, and `first_renewal` with `date`, `formatted_date`, `labelled`), and may have `coupons`, `shipping` (shaped like the cart's `shipping`), `fees` (keyed by fee ID) and `taxes`. Milo Subscriptions sends no `coupons` or `label`.

### Gifting

- Cart item `gift_recipient`: `email`.
- Product `gifting`: `giftable` (bool).

### Bookings and accommodation

- Cart item `booking_data`: `start_date`, `end_date`, `all_day` (bool), `resource_id` (int), `persons` (list of int), `cost` (minor units).
- Product `booking_data`: `duration_type`, `duration_unit`, `duration` (int), `has_persons` (bool), `min_persons`, `max_persons` (int), `has_resources` (bool), `resource_label`, `booking_location`.
- Cart item `accommodation_booking_data`: `check_in`, `check_out`.
- Product `accommodation_booking_data`: `min_nights`, `max_nights` (int), `check_in_time`, `check_out_time`.

### Composite Products and Product Bundles

A child item's `quantity` is `value`, `minimum` and `maximum` (int, `maximum` may be null).

- Cart item `composite_data`: `components` keyed by component ID (each: `id`, `quantity`, `variation`, `discount`, `optional`, `priced_individually`, `shipped_individually`, `title`) and `child_item_keys`.
- Product `composite_data`: `layout` and a list of `components` (each: `id`, `title`, `optional`, `quantity_min`, `quantity_max`, `priced_individually`, `discount`, `default_option_id`, `options_style`).
- Cart item `bundle_data`: `items` keyed by bundled item ID (each: `id`, `quantity`, `variation`, `discount`, `optional_selected`), `child_items` (the bundled items, which CoCart removes from the cart's own `items` list; each: `item_key`, `bundled_item_id`, `id`, `name`, `quantity`, `price`, `variation`) and `child_item_keys`.
- Product `bundle_data`: `layout` and a list of `items` (each: `id`, `optional`, `quantity`, `priced_individually`, `discount`).

### Product Add-Ons

- Cart item `addons`: a list of `field_label`, `field_type`, `value`, `price` (minor units), `price_type`.
- Product `addons`: a list of fields, each with `id`, `name`, `type`, `description`, `required`, `position`, `display`, `adjust_price`, `price`, `price_type`, `restrictions`, `min`, `max`, `limit_file_types`, `allowed_file_types` and `options` (each: `label`, `price`, `price_type`, `image`).

### Pricing and discounts

- `discount` (Discount Rules, product and cart item): `original_price`, `saved_amount` (minor units), and on cart items `is_free_item` (bool).
- Cart item `adp` (Advanced Dynamic Pricing): `original_price`, `saved_amount`, `is_free_item`, `rules` (titles of the rules applied).
- Product `msrp_data`: `msrp_price` for a simple product, `msrp_price_min` and `msrp_price_max` for a variable one; the rest are `''`.

### Other integrations

- Product `points_and_rewards`: `points_earned` (int), `max_discount` (minor units, `''` when the product sets no maximum).
- Cart `points_and_rewards`: `points_balance`, `points_to_earn` (int), `redemption_coupon` (the applied redemption coupon, or `''`).
- Product `quantity_rules` (Min/Max Quantities): `minimum`, `maximum` (may be null), `group_of` (int), `combine_variations` (bool).
- Product `vendor` (Dokan): `id` (0 with empty values when the seller isn't a vendor), `store_name`, `store_url`, `avatar`, `rating` (`average`, `count`).
- Product `condition` (Product Condition): `slug`, `label`, `schema_condition`, `custom_label`.
- Cart item `warranty` (WooCommerce Warranty): `label`, `type` (`included` or `addon`), `duration`, `cost`.
- Product `warranty`: `type`, `label`, and `options` (each: `key`, `duration`, `cost`).

## Sending the customer's choices

Some of this data describes a choice: which subscription plan, who receives a gift, which warranty. Send the choice when adding the item, as `add_item()` options:

```python
product = client.products().find(306).to_dict()

# Subscription plans: an option's `value` ("0" is one-time). Without it, the product's default applies.
for option in product["extensions"].get("subscription_schemes", []):
    if option["period"] == "/ month":
        client.cart().add_item(306, 1, convert_to_sub=option["value"])

# Gifting: the recipient's email.
client.cart().add_item(302, 1, recipient_email="friend@example.com")

# Warranty: an option's `key` from the product's `extensions.warranty.options`.
client.cart().add_item(154, 1, item_data={"warranty": "1-year"})
```

On a cart item the current subscription option is `selected`; switch it with `change_plan()`:

```python
item = client.cart().get().get_items()[0]

for option in item["extensions"].get("subscription_schemes", []):
    if not option["selected"]:
        client.cart().change_plan(item["item_key"], option["value"])
        break
```

## Data from other plugins

Any plugin can add data with CoCart's filters: `cocart_cart_extensions`, `cocart_cart_item_extensions` and `cocart_product_extensions`. It arrives the same way, under the plugin's own key:

```python
engraving = item["extensions"].get("engraving", {}).get("text")
```
