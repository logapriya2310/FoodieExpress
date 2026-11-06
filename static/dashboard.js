const role = document.body.dataset.role;
const stats = document.querySelector("#dashboardStats");
const content = document.querySelector("#dashboardContent");
const message = document.querySelector("#dashboardMessage");
const escapeText = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));
const cash = value => `₹${Number(value || 0).toLocaleString("en-IN")}`;

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request could not be completed.");
  return result;
}

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function statCard(label, value, note) {
  return `<article class="stat-card"><span>${escapeText(label)}</span><strong>${escapeText(value)}</strong><small>${escapeText(note)}</small></article>`;
}

async function loadDashboard() {
  try {
    if (role === "admin") await loadAdmin();
    else if (role === "chef") await loadChef();
    else if (role === "delivery_partner") await loadDelivery();
    else await loadCustomer();
  } catch (error) {
    if (error.message.includes("sign in")) window.location.assign(`/login?role=${encodeURIComponent(role)}`);
    else showMessage(error.message, true);
  }
}

async function loadChef() {
  const orders = await requestJson("/api/chef/orders");
  stats.innerHTML = [
    statCard("Open kitchen tickets", orders.length, "Orders assigned to your kitchen view"),
    statCard("Waiting for acceptance", orders.filter(order => order.chef_status === "Pending").length, "New orders to review"),
    statCard("Ready for pickup", orders.filter(order => order.chef_status === "Ready for Pickup").length, "Hand off to a delivery partner")
  ].join("");
  content.innerHTML = `<section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">KITCHEN QUEUE</div><h2>Incoming orders</h2></div><button class="text-button" data-refresh>Refresh ↻</button></div><div class="dashboard-order-list">${orders.length ? orders.map(order => `<article class="dashboard-order"><div class="order-title"><div><span class="order-number">ORDER #${order.id}</span><h3>${escapeText(order.customer_name)}</h3></div><span class="role-badge">${escapeText(order.chef_status)}</span></div><p>${escapeText(order.address)}</p><div class="order-footer"><strong>${cash(order.total)}</strong><button class="text-button" data-items="${order.id}">View items</button></div><div class="order-actions">${chefActions(order)}</div><div class="order-details hidden" id="items-${order.id}"></div></article>`).join("") : '<p class="empty-state">No kitchen tickets right now. New orders will appear here.</p>'}</div></section>`;
  content.querySelector("[data-refresh]").addEventListener("click", loadDashboard);
  content.querySelectorAll("[data-items]").forEach(button => button.addEventListener("click", () => showChefOrder(button.dataset.items)));
  content.querySelectorAll("[data-chef-status]").forEach(button => button.addEventListener("click", () => changeChefStatus(button.dataset.order, button.dataset.chefStatus)));
}

function chefActions(order) {
  if (order.chef_status === "Pending") return `<button class="button button-small" data-order="${order.id}" data-chef-status="Accepted">Accept order</button><button class="button button-small button-danger" data-order="${order.id}" data-chef-status="Rejected">Reject</button>`;
  if (order.chef_status === "Accepted") return `<button class="button button-small" data-order="${order.id}" data-chef-status="Preparing">Start preparing</button><button class="button button-small button-danger" data-order="${order.id}" data-chef-status="Rejected">Reject</button>`;
  if (order.chef_status === "Preparing") return `<button class="button button-small" data-order="${order.id}" data-chef-status="Ready for Pickup">Ready for pickup</button>`;
  return "";
}

async function showChefOrder(orderId) {
  try {
    const order = await requestJson(`/api/chef/orders/${orderId}`);
    const target = document.querySelector(`#items-${orderId}`);
    target.innerHTML = order.items.map(item => `<p>${escapeText(item.name)} × ${item.quantity} <span>${cash(item.unit_price * item.quantity)}</span></p>`).join("");
    target.classList.toggle("hidden");
  } catch (error) { showMessage(error.message, true); }
}

async function changeChefStatus(orderId, status) {
  try {
    await requestJson(`/api/chef/orders/${orderId}/status`, { method: "POST", body: JSON.stringify({ status }) });
    showMessage(`Order #${orderId} updated to ${status}.`);
    await loadChef();
  } catch (error) { showMessage(error.message, true); }
}

async function loadDelivery() {
  const orders = await requestJson("/api/partner/orders");
  stats.innerHTML = [
    statCard("Assigned deliveries", orders.length, "Only orders assigned to your account"),
    statCard("On the way", orders.filter(order => ["Picked Up", "On the Way"].includes(order.delivery_status)).length, "Update customers as you go"),
    statCard("Ready for pickup", orders.filter(order => order.delivery_status === "Ready for Pickup").length, "Collect from the kitchen")
  ].join("");
  content.innerHTML = `<section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">YOUR ASSIGNED ROUTE</div><h2>Delivery orders</h2></div><button class="text-button" data-refresh>Refresh ↻</button></div><div class="dashboard-order-list">${orders.length ? orders.map(order => `<article class="dashboard-order"><div class="order-title"><div><span class="order-number">ORDER #${order.id}</span><h3>${escapeText(order.customer_name)}</h3></div><span class="role-badge">${escapeText(order.delivery_status)}</span></div><p class="delivery-address">${escapeText(order.address)}</p><div class="simulated-mini-map" aria-label="Simulated delivery map"><span>● Partner location is simulated</span><i style="left:${Math.max(10, Math.min(80, 35 + (order.latitude - 12.9716) * 1000))}%"></i></div><div class="order-footer"><strong>${cash(order.total)}</strong><button class="button button-small" data-delivery-order="${order.id}" data-delivery-status="${nextDeliveryStatus(order.delivery_status)}" ${nextDeliveryStatus(order.delivery_status) ? "" : "disabled"}>${nextDeliveryStatus(order.delivery_status) || "Complete"}</button></div></article>`).join("") : '<p class="empty-state">No assigned deliveries yet. Your next route will show up here.</p>'}</div></section><p class="sim-note">Map marker is a demonstration of simulated location, not real GPS.</p>`;
  content.querySelector("[data-refresh]").addEventListener("click", loadDashboard);
  content.querySelectorAll("[data-delivery-order]").forEach(button => button.addEventListener("click", () => updateDelivery(button.dataset.deliveryOrder, button.dataset.deliveryStatus)));
}

function nextDeliveryStatus(current) {
  return { "Ready for Pickup": "Picked Up", "Picked Up": "On the Way", "On the Way": "Delivered" }[current] || "";
}

async function updateDelivery(orderId, status) {
  try {
    await requestJson(`/api/partner/orders/${orderId}/status`, { method: "POST", body: JSON.stringify({ status }) });
    showMessage(`Order #${orderId}: ${status}.`);
    await loadDelivery();
  } catch (error) { showMessage(error.message, true); }
}

async function loadCustomer() {
  const summary = await requestJson("/api/customer/summary");
  stats.innerHTML = [
    statCard("Your orders", summary.orders.length, "Your recent FoodieExpress visits"),
    statCard("Saved addresses", summary.addresses.length, "Up to five places you love"),
    statCard("Current orders", summary.orders.filter(order => !["Delivered", "Cancelled", "Rejected"].includes(order.status)).length, "Follow their progress below")
  ].join("");
  content.innerHTML = `<div class="customer-dashboard-grid"><section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">ORDER HISTORY</div><h2>Your orders</h2></div><a class="text-link" href="/#menu">Order something good ↗</a></div><div class="dashboard-order-list">${summary.orders.length ? summary.orders.map(order => `<article class="dashboard-order"><div class="order-title"><div><span class="order-number">ORDER #${order.id}</span><h3>${cash(order.total)}</h3></div><span class="role-badge">${escapeText(order.status)}</span></div><p>Placed ${escapeText(order.created_at)}</p><div class="order-actions"><button class="text-button" data-track-order="${order.id}">Track order</button>${["Pending", "Accepted"].includes(order.status) ? `<button class="text-button text-danger" data-cancel-order="${order.id}">Cancel order</button>` : ""}</div><div class="order-details hidden" id="tracking-${order.id}"></div></article>`).join("") : '<p class="empty-state">No orders yet. Your first favorite is waiting on the menu.</p>'}</div></section><section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">YOUR PLACES</div><h2>Saved addresses</h2></div></div><div class="saved-address-list">${summary.addresses.length ? summary.addresses.map(address => `<article class="saved-address"><strong>${escapeText(address.label)}</strong><p>${escapeText(address.address)}</p></article>`).join("") : '<p class="empty-state">Save an address at checkout to find it here next time.</p>'}</div><div class="dashboard-promo"><span>✦ FESTIVE SPECIAL</span><strong>Good things taste better together.</strong><p>Browse recommended food combos and Diwali offers.</p><a class="text-link" href="/#recommendations">See what’s cooking →</a></div></section></div>`;
  content.querySelectorAll("[data-cancel-order]").forEach(button => button.addEventListener("click", () => cancelOrder(button.dataset.cancelOrder)));
  content.querySelectorAll("[data-track-order]").forEach(button => button.addEventListener("click", () => trackOrder(button.dataset.trackOrder)));
}

async function trackOrder(orderId) {
  try {
    const order = await requestJson(`/api/orders/${orderId}`);
    const target = document.querySelector(`#tracking-${orderId}`);
    const location = order.delivery_assignment;
    target.innerHTML = `<div class="tracking-map dashboard-map"><span class="map-road"></span><span class="map-road two"></span>${location ? `<span class="map-pin partner" style="left:${Math.max(14, Math.min(76, 20 + (location.latitude - 12.9716) * 700))}%;top:35%"></span><span class="map-dot-label map-label-partner">${escapeText(location.partner_name)} · simulated</span>` : '<span class="map-dot-label map-label-partner">Partner assignment pending</span>'}<span class="map-pin home">⌂</span></div><p class="tracking-caption">Order status: ${escapeText(order.status)}. ${escapeText(order.tracking_note)}</p><div class="tracking-items">${order.items.map(item => `<p>${escapeText(item.name)} × ${item.quantity}</p>`).join("")}</div>`;
    target.classList.toggle("hidden");
  } catch (error) { showMessage(error.message, true); }
}

async function cancelOrder(orderId) {
  try {
    await requestJson(`/api/customer/orders/${orderId}/cancel`, { method: "POST", body: JSON.stringify({}) });
    showMessage(`Order #${orderId} cancelled.`);
    await loadCustomer();
  } catch (error) { showMessage(error.message, true); }
}

async function loadAdmin() {
  const data = await requestJson("/api/admin/summary");
  stats.innerHTML = [
    statCard("Recorded sales", cash(data.stats.sales), "Excludes cancelled orders"),
    statCard("All orders", data.stats.order_count || 0, `${data.stats.active_orders || 0} in progress`),
    statCard("Customers", data.stats.customers, `${data.stats.chefs} chefs · ${data.stats.partners} delivery partners`)
  ].join("");
  content.innerHTML = `<div class="admin-dashboard-grid">
    <section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">YOUR PEOPLE</div><h2>Team & customers</h2></div></div><form id="staffForm" class="inline-admin-form"><input name="name" required minlength="2" maxlength="100" placeholder="Full name"><input name="email" type="email" required maxlength="254" placeholder="Email"><input name="password" type="password" required minlength="8" maxlength="256" placeholder="Temporary password"><select name="role"><option value="chef">Chef</option><option value="delivery_partner">Delivery partner</option></select><button class="button button-small" type="submit">Create account</button></form><div class="user-list">${data.users.map(user => `<article class="admin-list-row"><span><strong>${escapeText(user.name)}</strong><small>${escapeText(user.email)} · ${escapeText(user.role.replace("_", " "))}</small></span>${user.role !== "admin" ? `<button class="text-button" data-user-id="${user.id}" data-user-active="${user.active ? "false" : "true"}">${user.active ? "Disable" : "Enable"}</button>` : '<span class="role-badge">Owner</span>'}</article>`).join("")}</div></section>
    <section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">MENU MANAGEMENT</div><h2>Food & categories</h2></div></div><form id="foodForm" class="inline-admin-form"><input name="name" required maxlength="120" placeholder="Dish name"><input name="description" required maxlength="500" placeholder="Description"><input name="price" type="number" min="1" required placeholder="Price ₹"><input name="category" list="categoryOptions" required placeholder="Category"><datalist id="categoryOptions">${data.categories.map(category => `<option value="${escapeText(category.name)}">`).join("")}</datalist><input name="emoji" maxlength="12" placeholder="Emoji"><input name="image" type="url" placeholder="Image URL (HTTPS)"><button class="button button-small" type="submit">Add food</button></form><form id="categoryForm" class="inline-admin-form compact-admin-form"><input name="name" minlength="2" maxlength="60" required placeholder="New category"><button class="button button-small button-light" type="submit">Add category</button></form><div class="admin-food-list">${data.foods.map(food => `<form class="admin-food" data-admin-food="${food.id}"><strong>${escapeText(food.name)}</strong><input aria-label="Price for ${escapeText(food.name)}" name="price" type="number" min="1" value="${food.price}" required><input aria-label="Category for ${escapeText(food.name)}" name="category" list="categoryOptions" value="${escapeText(food.category)}"><label><input name="available" type="checkbox" ${food.available ? "checked" : ""}> Available</label><button class="add-button" type="submit">Save</button></form>`).join("")}</div></section>
    <section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">KITCHEN & DELIVERY</div><h2>Order assignments</h2></div></div><div class="admin-order-list">${data.orders.map(order => `<article class="admin-manage-order"><div class="order-title"><strong>Order #${order.id} · ${cash(order.total)}</strong><span class="role-badge">${escapeText(order.status)}</span></div><p>${escapeText(order.customer_name)} · ${escapeText(order.address)}</p><div class="assignment-controls"><label>Chef<select data-assign-chef="${order.id}"><option value="">${order.chef_name ? escapeText(order.chef_name) : "Assign chef"}</option>${data.staff.filter(user => user.role === "chef" && user.active).map(user => `<option value="${user.id}" ${String(user.id) === String(order.chef_user_id) ? "selected" : ""}>${escapeText(user.name)}</option>`).join("")}</select></label><label>Delivery partner<select data-assign-delivery="${order.id}"><option value="">${order.partner_name ? escapeText(order.partner_name) : "Assign partner"}</option>${data.staff.filter(user => user.role === "delivery_partner" && user.active).map(user => `<option value="${user.id}" ${String(user.id) === String(order.partner_user_id) ? "selected" : ""}>${escapeText(user.name)}</option>`).join("")}</select></label><label>Order status<select data-admin-order-status="${order.id}"><option ${order.status === "Pending" ? "selected" : ""}>Pending</option><option ${order.status === "Accepted" ? "selected" : ""}>Accepted</option><option ${order.status === "Preparing" ? "selected" : ""}>Preparing</option><option ${order.status === "Ready for Pickup" ? "selected" : ""}>Ready for Pickup</option><option ${order.status === "Picked Up" ? "selected" : ""}>Picked Up</option><option ${order.status === "On the Way" ? "selected" : ""}>On the Way</option><option ${order.status === "Delivered" ? "selected" : ""}>Delivered</option><option ${order.status === "Cancelled" ? "selected" : ""}>Cancelled</option><option ${order.status === "Rejected" ? "selected" : ""}>Rejected</option></select></label></div></article>`).join("") || '<p class="empty-state">Orders will appear here when customers check out.</p>'}</div></section>
    <section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">FESTIVE & DAILY OFFERS</div><h2>Coupons</h2></div></div><form id="offerForm" class="inline-admin-form"><input name="title" required maxlength="100" placeholder="Offer title"><input name="description" maxlength="300" placeholder="Offer description"><input name="code" required maxlength="30" placeholder="Coupon code"><input name="discount_percent" type="number" min="0" max="100" value="10" required placeholder="Discount %"><input name="category" list="categoryOptions" placeholder="Optional category"><input name="minimum_subtotal" type="number" min="0" value="0" placeholder="Minimum subtotal"><label class="inline-checkbox"><input name="free_delivery" type="checkbox"> Free delivery</label><button class="button button-small" type="submit">Create offer</button></form><div class="user-list">${data.offers.map(offer => `<article class="admin-list-row"><span><strong>${escapeText(offer.title)} · ${escapeText(offer.code)}</strong><small>${offer.discount_percent}% off${offer.category ? ` · ${escapeText(offer.category)}` : ""}${offer.free_delivery ? " · Free delivery" : ""}</small></span><button class="text-button" data-offer-id="${offer.id}" data-offer-active="${offer.active ? "false" : "true"}">${offer.active ? "Disable" : "Enable"}</button></article>`).join("")}</div></section>
  </div>`;
  wireAdmin(data);
}

function wireAdmin(data) {
  document.querySelector("#staffForm").addEventListener("submit", async event => {
    event.preventDefault();
    await adminAction("/api/admin/users", Object.fromEntries(new FormData(event.currentTarget)), "Account created.");
  });
  document.querySelector("#foodForm").addEventListener("submit", async event => {
    event.preventDefault();
    await adminAction("/api/admin/foods", Object.fromEntries(new FormData(event.currentTarget)), "Menu item added.");
  });
  document.querySelector("#categoryForm").addEventListener("submit", async event => {
    event.preventDefault();
    await adminAction("/api/admin/categories", Object.fromEntries(new FormData(event.currentTarget)), "Category added.");
  });
  document.querySelector("#offerForm").addEventListener("submit", async event => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    payload.free_delivery = event.currentTarget.elements.free_delivery.checked;
    await adminAction("/api/admin/offers", payload, "Offer created.");
  });
  content.querySelectorAll("[data-admin-food]").forEach(form => form.addEventListener("submit", async event => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form));
    values.available = form.elements.available.checked;
    await adminAction(`/api/admin/foods/${form.dataset.adminFood}`, values, "Menu item updated.");
  }));
  content.querySelectorAll("[data-user-id]").forEach(button => button.addEventListener("click", () =>
    adminAction(`/api/admin/users/${button.dataset.userId}/active`, { active: button.dataset.userActive === "true" }, "Account status updated.")
  ));
  content.querySelectorAll("[data-offer-id]").forEach(button => button.addEventListener("click", () =>
    adminAction(`/api/admin/offers/${button.dataset.offerId}/active`, { active: button.dataset.offerActive === "true" }, "Offer status updated.")
  ));
  content.querySelectorAll("[data-assign-chef]").forEach(select => select.addEventListener("change", () => {
    if (select.value) adminAction(`/api/admin/orders/${select.dataset.assignChef}/chef`, { chef_user_id: select.value }, "Chef assigned.");
  }));
  content.querySelectorAll("[data-assign-delivery]").forEach(select => select.addEventListener("change", () => {
    if (select.value) adminAction(`/api/admin/orders/${select.dataset.assignDelivery}/delivery`, { partner_user_id: select.value }, "Delivery partner assigned.");
  }));
  content.querySelectorAll("[data-admin-order-status]").forEach(select => select.addEventListener("change", () =>
    adminAction(`/api/admin/orders/${select.dataset.adminOrderStatus}/status`, { status: select.value }, "Order status updated.")
  ));
}

async function adminAction(path, payload, success) {
  try {
    await requestJson(path, { method: "POST", body: JSON.stringify(payload) });
    showMessage(success);
    await loadAdmin();
  } catch (error) { showMessage(error.message, true); }
}

document.addEventListener("DOMContentLoaded", loadDashboard);
