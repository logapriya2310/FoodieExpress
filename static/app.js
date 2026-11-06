let categories = [
  ["All", "✦"], ["Breakfast", "🍳"], ["Lunch", "🍲"], ["Dinner", "🍽️"],
  ["Snacks", "🥟"], ["Desserts", "🍰"], ["Beverages", "🥤"],
  ["Vegetarian", "🥬"], ["Non-Vegetarian", "🍗"]
];
function readStoredArray(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}
const state = {
  foods: [], cart: readStoredArray("foodie-cart").filter(item => Number.isInteger(item.id) && Number.isInteger(item.quantity) && item.quantity > 0),
  favorites: readStoredArray("foodie-favorites").filter(Number.isInteger),
  category: "All", coupon: ["DIWALI20", "WELCOME10"].includes(localStorage.getItem("foodie-coupon")) ? localStorage.getItem("foodie-coupon") : "", authMode: "login", customer: null, toastTimer: null
};
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const money = value => `₹${Number(value).toLocaleString("en-IN")}`;
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));
async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  let data;
  try { data = await response.json(); } catch { throw new Error("The server returned an unexpected response."); }
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}
function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}
function openDialog(id) { $(id).showModal(); }
function persistCart() {
  localStorage.setItem("foodie-cart", JSON.stringify(state.cart));
  localStorage.setItem("foodie-coupon", state.coupon);
  renderCart();
}
function findFood(id) { return state.foods.find(food => food.id === Number(id)); }
function setCategory(category) {
  state.category = category;
  $$(".category-tile, .filter-chip").forEach(button => button.classList.toggle("active", button.dataset.category === category));
  loadMenu();
  $("#menu").scrollIntoView({ behavior: "smooth" });
}
async function renderCategories() {
  const known = new Set(categories.map(([name]) => name));
  const dynamicCategories = await api("/api/categories");
  categories = [
    ...categories,
    ...dynamicCategories
      .filter(category => !known.has(category.name))
      .map(category => [category.name, "🍽️"])
  ];
  $("#categoryList").innerHTML = categories.slice(1).map(([name, icon]) =>
    `<button class="category-tile" data-category="${escapeHTML(name)}"><span class="category-emoji">${icon}</span><span>${escapeHTML(name)}</span></button>`
  ).join("");
  $("#filterChips").innerHTML = categories.map(([name]) =>
    `<button class="filter-chip ${name === state.category ? "active" : ""}" data-category="${escapeHTML(name)}">${escapeHTML(name)}</button>`
  ).join("");
  $$("[data-category]").forEach(button => button.addEventListener("click", () => setCategory(button.dataset.category)));
}
async function loadMenu() {
  const params = new URLSearchParams();
  const query = $("#foodSearch").value.trim();
  const maxPrice = $("#priceFilter").value.trim();
  if (state.category !== "All") params.set("category", state.category);
  if (query) params.set("q", query);
  if (maxPrice) params.set("max_price", maxPrice);
  try {
    const visibleFoods = await api(`/api/menu?${params}`);
    const cachedFoods = new Map(state.foods.map(food => [food.id, food]));
    visibleFoods.forEach(food => cachedFoods.set(food.id, food));
    state.foods = [...cachedFoods.values()];
    $("#foodGrid").innerHTML = visibleFoods.map(foodCard).join("");
    $("#menuEmpty").classList.toggle("hidden", visibleFoods.length > 0);
    renderCart();
  } catch (error) {
    $("#foodGrid").innerHTML = `<p class="form-message">${escapeHTML(error.message)}</p>`;
  }
}
function foodCard(food) {
  const isFavorite = state.favorites.includes(food.id);
  const addControl = food.available
    ? `<button class="add-button" data-add="${food.id}"><span>＋</span> Add</button>`
    : '<span class="sold-out">Sold out</span>';
  return `<article class="food-card"><div class="food-photo"><span class="photo-fallback" aria-hidden="true">${escapeHTML(food.emoji)}</span><img src="${escapeHTML(food.image)}" alt="${escapeHTML(food.name)}" loading="lazy" onerror="this.style.display='none'"><span class="food-tag">${food.available ? escapeHTML(food.category) : "SOLD OUT"}</span><button class="favorite-button ${isFavorite ? "active" : ""}" data-favorite="${food.id}" aria-label="${isFavorite ? "Remove from" : "Add to"} favorites">${isFavorite ? "♥" : "♡"}</button></div><div class="food-info"><div class="food-title-row"><h3>${escapeHTML(food.name)}</h3><span class="rating">★ ${Number(food.rating).toFixed(1)}</span></div><p>${escapeHTML(food.description)}</p><div class="food-card-bottom"><span class="food-price">${money(food.price)}</span>${addControl}</div></div></article>`;
}
function addToCart(id, quantity = 1) {
  const food = findFood(id);
  if (!food) { toast("That dish is not available in this menu."); return; }
  const item = state.cart.find(entry => entry.id === food.id);
  if (item) item.quantity = Math.min(20, item.quantity + quantity);
  else state.cart.push({ id: food.id, quantity: Math.min(20, quantity) });
  persistCart();
  toast(`${food.name} added to your bag.`);
}
function renderCart() {
  const count = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  $("#cartCount").textContent = count;
  $("#cartHeadingCount").textContent = `(${count})`;
  const cartItems = state.cart.map(item => ({ ...item, food: findFood(item.id) })).filter(item => item.food);
  if (!cartItems.length) {
    $("#cartLines").innerHTML = '<div class="cart-empty">Your bag is taking a little break. Let’s find something lovely.</div>';
  } else {
    $("#cartLines").innerHTML = cartItems.map(({ food, quantity }) => `<div class="cart-line"><img src="${escapeHTML(food.image)}" alt="" onerror="this.style.display='none'"><div><strong>${escapeHTML(food.name)}</strong><small>${money(food.price)} each</small><div class="quantity-control"><button data-quantity="-1" data-id="${food.id}" aria-label="Decrease quantity">−</button><span>${quantity}</span><button data-quantity="1" data-id="${food.id}" aria-label="Increase quantity">＋</button><button class="remove-item" data-remove="${food.id}">Remove</button></div></div><span class="cart-line-total">${money(food.price * quantity)}</span></div>`).join("");
  }
  const subtotal = cartItems.reduce((sum, item) => sum + item.food.price * item.quantity, 0);
  const eligibleSubtotal = cartItems.reduce((sum, item) =>
    sum + (item.food.category === "Desserts" ? item.food.price * item.quantity : 0), 0);
  const discount = state.coupon === "DIWALI20" ? Math.round(eligibleSubtotal * .2) : state.coupon === "WELCOME10" ? Math.round(subtotal * .1) : 0;
  const deliveryFee = subtotal >= 499 ? 0 : 39;
  $("#cartSubtotal").textContent = money(subtotal);
  $("#cartDiscount").textContent = `−${money(discount)}`;
  $("#cartDeliveryFee").textContent = deliveryFee ? money(deliveryFee) : "Free";
  $("#cartTotal").textContent = money(subtotal - discount + deliveryFee);
  $("#discountRow").classList.toggle("hidden", discount === 0);
  $("#couponInput").value = state.coupon;
}
function cartPayload() { return state.cart.map(({ id, quantity }) => ({ id, quantity })); }
async function applyCoupon(code) {
  if (!state.cart.length) { toast("Add something delicious before applying a coupon."); return; }
  const normalizedCode = String(code || "").trim().toUpperCase();
  if (!normalizedCode) {
    $("#couponMessage").textContent = "Enter a coupon code to apply.";
    return;
  }
  if (!["DIWALI20", "WELCOME10"].includes(normalizedCode)) {
    $("#couponMessage").textContent = "That coupon code isn't valid. Try DIWALI20 or WELCOME10.";
    return;
  }
  if (normalizedCode === "DIWALI20" && !state.cart.some(item => findFood(item.id)?.category === "Desserts")) {
    $("#couponMessage").textContent = "DIWALI20 applies to selected sweets. Add a dessert to your bag.";
    return;
  }
  try {
    const result = await api("/api/coupons/apply", {
      method: "POST", body: JSON.stringify({ code: normalizedCode, items: cartPayload() })
    });
    state.coupon = result.code;
    persistCart();
    $("#couponMessage").textContent = `${result.code} applied — saving ${money(result.discount)}.`;
    toast("Lovely. Your discount is on.");
  } catch (error) {
    state.coupon = "";
    persistCart();
    $("#couponMessage").textContent = error.message;
  }
}
async function loadCombos() {
  try {
    const combos = await api("/api/recommendations");
    $("#comboGrid").innerHTML = combos.map((combo, index) => `<article class="combo-card"><div class="combo-image"><img src="${escapeHTML(combo.image)}" alt="${escapeHTML(combo.name)} combination" loading="lazy" onerror="this.style.display='none'"><span>${escapeHTML(combo.tag)}</span></div><div class="combo-info"><h3>${escapeHTML(combo.name)}</h3><p>${escapeHTML(combo.description)}</p><div class="combo-foot"><strong>${money(combo.price)}</strong><button class="add-button" data-combo="${index}">Add combo</button></div></div></article>`).join("");
    $$("#comboGrid [data-combo]").forEach(button => button.addEventListener("click", () => {
      const combo = combos[Number(button.dataset.combo)];
      combo.items.forEach(id => addToCart(id));
      openDialog("#cartDialog");
    }));
    $("#comboGrid").dataset.combos = JSON.stringify(combos);
  } catch (error) {
    $("#comboGrid").innerHTML = `<p class="form-message">${escapeHTML(error.message)}</p>`;
  }
}
async function loadReviews() {
  try {
    const reviews = await api("/api/reviews");
    $("#reviewGrid").innerHTML = reviews.map(review => {
      const initial = escapeHTML(review.name.trim().charAt(0).toUpperCase() || "?");
      return `<article class="review-card"><div class="review-stars" aria-label="${review.rating} out of 5 stars">${"★".repeat(review.rating)}${"☆".repeat(5 - review.rating)}</div><blockquote>“${escapeHTML(review.feedback)}”</blockquote><div class="review-person"><span class="review-avatar">${initial}</span><span><strong>${escapeHTML(review.name)}</strong><small>Ordered ${escapeHTML(review.food)}</small></span></div></article>`;
    }).join("");
  } catch (error) { $("#reviewGrid").innerHTML = `<p class="form-message">${escapeHTML(error.message)}</p>`; }
}
async function loadCustomer() {
  const result = await api("/api/auth/me");
  state.customer = result.customer;
  $("#loginOpen").textContent = state.customer ? (state.customer.role === "admin" ? "Admin" : state.customer.role === "partner" ? "Partner" : `Hi, ${state.customer.name.split(" ")[0]}`) : "Sign in";
  $("#logoutOpen").classList.toggle("hidden", !state.customer);
  $("#customerNameField").classList.toggle("hidden", Boolean(state.customer && state.customer.role === "customer"));
  $("#checkoutForm [name=name]").required = !state.customer || state.customer.role !== "customer";
  if (state.customer?.role === "customer") $("#checkoutForm [name=name]").value = state.customer.name;
  $("#savedAddressTools").classList.toggle("hidden", state.customer?.role !== "customer");
  if (state.customer?.role === "customer") await loadAddresses();
}
async function loadAddresses() {
  const addresses = await api("/api/addresses");
  $("#savedAddressSelect").innerHTML = `<option value="">Use a saved address</option>${addresses.map(address => `<option value="${address.id}" data-address="${escapeHTML(address.address)}">${escapeHTML(address.label)} · ${escapeHTML(address.address)}</option>`).join("")}`;
}
function selectAuthMode(mode) {
  state.authMode = mode;
  $$(".auth-tabs button").forEach(button => button.classList.toggle("active", button.dataset.authMode === mode));
  $$(".register-only").forEach(node => node.classList.toggle("hidden", mode !== "register"));
  $(".login-role-field").classList.toggle("hidden", mode !== "login");
  $("#authTitle").textContent = mode === "register" ? "Let’s get to know you." : "Welcome back.";
  $("#authForm [name=password]").autocomplete = mode === "register" ? "new-password" : "current-password";
  $("#authForm [name=name]").required = mode === "register";
  $("#authMessage").textContent = "";
}
function openSignIn() {
  selectAuthMode("login");
  openDialog("#authDialog");
}
function rememberOrder(orderId, trackingToken) {
  localStorage.setItem("foodie-last-order", JSON.stringify({ id: orderId, token: trackingToken }));
  $("#lastOrderOpen").classList.remove("hidden");
}
async function placeOrder(event) {
  event.preventDefault();
  if (!state.cart.length) { toast("Your bag is empty. Add a dish first."); return; }
  const formElement = event.currentTarget;
  const form = new FormData(formElement);
  const addressLabel = $("#addressLabel").value.trim();
  try {
    const result = await api("/api/orders", {
      method: "POST",
      body: JSON.stringify({ items: cartPayload(), coupon: state.coupon, name: form.get("name"), address: form.get("address") })
    });
    state.cart = [];
    state.coupon = "";
    persistCart();
    formElement.reset();
    $("#cartDialog").close();
    rememberOrder(result.order_id, result.tracking_token);
    if (state.customer?.role === "customer" && addressLabel) {
      try {
        await api("/api/addresses", { method: "POST", body: JSON.stringify({ label: addressLabel, address: form.get("address") }) });
      } catch (error) { toast(error.message); }
    }
    toast("Order placed. A little deliciousness is on the way!");
    await showTracking(result.order_id, result.tracking_token);
  } catch (error) { toast(error.message); }
}
async function showTracking(orderId, trackingToken = "") {
  try {
    const tokenQuery = trackingToken ? `?token=${encodeURIComponent(trackingToken)}` : "";
    const order = await api(`/api/orders/${encodeURIComponent(orderId)}${tokenQuery}`);
    $("#trackingNumber").textContent = `#${order.id}`;
    $("#trackingBody").innerHTML = `<div class="tracking-card"><div class="tracking-status"><strong>${escapeHTML(order.status)}</strong><span>Estimated arrival · 25–35 min</span></div><div class="tracking-map" aria-label="Illustrated delivery map. The delivery partner location is simulated."><span class="map-road"></span><span class="map-road two"></span><span class="map-pin partner">●</span><span class="map-pin home">⌂</span><span class="map-dot-label map-label-partner">Your rider</span><span class="map-dot-label map-label-home">You</span></div><p class="tracking-caption">Demo map only — partner position is simulated and does not use real GPS. Your order status: ${escapeHTML(order.status)}.</p><div class="tracking-items">${order.items.map(item => `<p>${escapeHTML(item.name)} × ${item.quantity}</p>`).join("")}</div><div class="tracking-total"><span>Total paid</span><span>${money(order.total)}</span></div></div>`;
    openDialog("#trackingDialog");
    const pin = $(".map-pin.partner");
    let step = 0;
    const points = [["19%", "20%"], ["33%", "31%"], ["47%", "46%"], ["63%", "39%"], ["76%", "59%"]];
    const timer = setInterval(() => {
      if (!$("#trackingDialog").open || !pin.isConnected) { clearInterval(timer); return; }
      const [left, top] = points[step++ % points.length];
      pin.style.left = left;
      pin.style.top = top;
    }, 1900);
  } catch (error) { toast(error.message); }
}
async function showHistory() {
  if (!state.customer || state.customer.role !== "customer") { openSignIn(); return; }
  try {
    const orders = await api("/api/orders");
    $("#historyBody").innerHTML = orders.length ? orders.map(order => `<article class="history-order"><div><strong>Order #${order.id}</strong><strong>${money(order.total)}</strong></div><p>${escapeHTML(order.status)} · ${escapeHTML(order.created_at)}</p><button data-track="${order.id}">Track order</button><button data-reorder="${order.id}">Order again</button></article>`).join("") : '<p class="cart-empty">Your first delicious order is waiting to happen.</p>';
    $$("#historyBody [data-track]").forEach(button => button.addEventListener("click", () => {
      $("#historyDialog").close();
      showTracking(button.dataset.track);
    }));
    $$("#historyBody [data-reorder]").forEach(button => button.addEventListener("click", async () => {
      try {
        const order = await api(`/api/orders/${button.dataset.reorder}`);
        order.items.forEach(item => {
          const existing = state.cart.find(entry => entry.id === item.food_id);
          if (existing) existing.quantity = Math.min(20, existing.quantity + item.quantity);
          else state.cart.push({ id: item.food_id, quantity: Math.min(20, item.quantity) });
        });
        persistCart();
        $("#historyDialog").close();
        openDialog("#cartDialog");
        toast("Your old favorites are back in your bag.");
      } catch (error) { toast(error.message); }
    }));
    openDialog("#historyDialog");
  } catch (error) { toast(error.message); if (error.message.includes("sign in")) openSignIn(); }
}
async function showPartnerDashboard() {
  if (!state.customer || state.customer.role !== "partner") {
    openSignIn();
    return;
  }
  try {
    const orders = await api("/api/partner/orders");
    $("#partnerBody").innerHTML = orders.length ? orders.map(order => `<article class="partner-order"><div><strong>Order #${order.id} · ${money(order.total)}</strong><p>${escapeHTML(order.customer_name)}<br>${escapeHTML(order.address)}</p></div><span class="rating">${escapeHTML(order.status)}</span><select data-status="${order.id}" aria-label="Update status for order ${order.id}"><option ${order.status === "Preparing" ? "selected" : ""}>Preparing</option><option ${order.status === "Picked up" ? "selected" : ""}>Picked up</option><option ${order.status === "On the way" ? "selected" : ""}>On the way</option><option ${order.status === "Delivered" ? "selected" : ""}>Delivered</option></select></article>`).join("") : '<p class="cart-empty">No orders have been placed yet.</p>';
    $$("#partnerBody [data-status]").forEach(select => select.addEventListener("change", async () => {
      try {
        await api(`/api/partner/orders/${select.dataset.status}/status`, { method: "POST", body: JSON.stringify({ status: select.value }) });
        toast(`Order status updated to ${select.value}.`);
      } catch (error) {
        toast(error.message);
        if (error.message.includes("delivery partner account")) openSignIn();
      }
    }));
    openDialog("#partnerDialog");
  } catch (error) {
    toast(error.message);
    if (error.message.includes("delivery partner account")) openSignIn();
  }
}
async function showAdminDashboard() {
  if (!state.customer || state.customer.role !== "admin") {
    openSignIn();
    return;
  }
  try {
    const summary = await api("/api/admin/summary");
    $("#adminBody").innerHTML = `<h3>Food menu</h3>${summary.foods.map(food => `<form class="admin-food" data-admin-food="${food.id}"><strong>${escapeHTML(food.name)}</strong><input aria-label="Price for ${escapeHTML(food.name)}" name="price" type="number" min="1" value="${food.price}" required><label><input name="available" type="checkbox" ${food.available ? "checked" : ""}> Available</label><button class="add-button" type="submit">Save</button></form>`).join("")}<h3>Recent orders</h3>${summary.orders.map(order => `<article class="history-order"><div><strong>#${order.id} · ${escapeHTML(order.customer_name)}</strong><strong>${money(order.total)}</strong></div><p>${escapeHTML(order.status)} · ${escapeHTML(order.address)}</p></article>`).join("")}<h3>Customers (${summary.customers.length})</h3>${summary.customers.map(customer => `<article class="history-order"><div><strong>${escapeHTML(customer.name)}</strong><span>${escapeHTML(customer.email)}</span></div></article>`).join("")}`;
    $$("#adminBody [data-admin-food]").forEach(form => form.addEventListener("submit", async event => {
      event.preventDefault();
      const data = new FormData(form);
      try {
        await api(`/api/admin/foods/${form.dataset.adminFood}`, { method: "POST", body: JSON.stringify({ price: data.get("price"), available: data.has("available") }) });
        toast("Menu item saved.");
        await loadMenu();
      } catch (error) { toast(error.message); }
    }));
    openDialog("#adminDialog");
  } catch (error) {
    toast(error.message);
    if (error.message.includes("admin account")) openSignIn();
  }
}
async function submitReview(event) {
  event.preventDefault();
  if (!state.customer || state.customer.role !== "customer") {
    openSignIn();
    return;
  }
  const formElement = event.currentTarget;
  const data = new FormData(formElement);
  try {
    await api("/api/reviews", { method: "POST", body: JSON.stringify({ food: data.get("food"), rating: data.get("rating"), feedback: data.get("feedback") }) });
    $("#reviewMessage").textContent = "Thanks for sharing the love! Your review is up.";
    formElement.reset();
    await loadReviews();
  } catch (error) {
    $("#reviewMessage").textContent = error.message;
    if (error.message.includes("sign in")) openSignIn();
  }
}
async function submitAuth(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  const data = new FormData(formElement);
  const endpoint = state.authMode === "register" ? "/api/auth/register" : "/api/auth/login";
  try {
    const result = await api(endpoint, { method: "POST", body: JSON.stringify({
      name: data.get("name"), email: data.get("email"), password: data.get("password"),
      role: state.authMode === "register" ? "customer" : data.get("role")
    }) });
    await loadCustomer();
    $("#authDialog").close();
    formElement.reset();
    window.location.assign(result.redirect);
  } catch (error) { $("#authMessage").textContent = error.message; }
}
function init() {
  renderCategories().catch(error => toast(error.message));
  loadMenu();
  loadCombos();
  loadReviews();
  loadCustomer().catch(error => toast(error.message));
  renderCart();

  $("#foodGrid").addEventListener("click", event => {
    const add = event.target.closest("[data-add]");
    const favorite = event.target.closest("[data-favorite]");
    if (add) addToCart(add.dataset.add);
    if (favorite) {
      const id = Number(favorite.dataset.favorite);
      state.favorites = state.favorites.includes(id) ? state.favorites.filter(item => item !== id) : [...state.favorites, id];
      localStorage.setItem("foodie-favorites", JSON.stringify(state.favorites));
      favorite.classList.toggle("active");
      favorite.textContent = favorite.classList.contains("active") ? "♥" : "♡";
    }
  });
  $("#cartLines").addEventListener("click", event => {
    const quantity = event.target.closest("[data-quantity]");
    const remove = event.target.closest("[data-remove]");
    if (quantity) {
      const item = state.cart.find(entry => entry.id === Number(quantity.dataset.id));
      if (item) item.quantity += Number(quantity.dataset.quantity);
      state.cart = state.cart.filter(entry => entry.quantity > 0).map(entry => ({ ...entry, quantity: Math.min(20, entry.quantity) }));
      persistCart();
    }
    if (remove) {
      state.cart = state.cart.filter(entry => entry.id !== Number(remove.dataset.remove));
      persistCart();
    }
  });
  $("#cartOpen").addEventListener("click", () => openDialog("#cartDialog"));
  $("#heroOrder").addEventListener("click", () => state.cart.length ? openDialog("#cartDialog") : $("#menu").scrollIntoView({ behavior: "smooth" }));
  $("#loginOpen").addEventListener("click", () => {
    if (state.customer) window.location.assign(`/dashboard/${state.customer.role}`);
    else window.location.assign("/login");
  });
  $("#applyCoupon").addEventListener("click", () => applyCoupon($("#couponInput").value));
  $("#offerCoupon").addEventListener("click", () => { $("#couponInput").value = "DIWALI20"; openDialog("#cartDialog"); applyCoupon("DIWALI20"); });
  $("#checkoutForm").addEventListener("submit", placeOrder);
  $("#authForm").addEventListener("submit", submitAuth);
  $("#reviewForm").addEventListener("submit", submitReview);
  $("#historyOpen").addEventListener("click", showHistory);
  $("#logoutOpen").addEventListener("click", async () => {
    try {
      await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
      await loadCustomer();
      toast("You are signed out.");
    } catch (error) { toast(error.message); }
  });
  $("#lastOrderOpen").addEventListener("click", () => {
    let order = null;
    try { order = JSON.parse(localStorage.getItem("foodie-last-order") || "null"); } catch { order = null; }
    if (order) showTracking(order.id, order.token);
  });
  $("#partnerOpen").addEventListener("click", showPartnerDashboard);
  $("#adminOpen").addEventListener("click", showAdminDashboard);
  $("#savedAddressSelect").addEventListener("change", event => {
    const option = event.target.selectedOptions[0];
    if (option?.dataset.address) $("#deliveryAddress").value = option.dataset.address;
  });
  $("#saveAddressButton").addEventListener("click", async () => {
    try {
      const saved = await api("/api/addresses", { method: "POST", body: JSON.stringify({ label: $("#addressLabel").value.trim(), address: $("#deliveryAddress").value.trim() }) });
      await loadAddresses();
      $("#savedAddressSelect").value = String(saved.id);
      toast("Delivery address saved.");
    } catch (error) { toast(error.message); }
  });
  $("#deleteAddressButton").addEventListener("click", async () => {
    const id = $("#savedAddressSelect").value;
    if (!id) { toast("Choose a saved address to remove."); return; }
    try {
      await api(`/api/addresses/${id}`, { method: "DELETE" });
      $("#savedAddressSelect").value = "";
      await loadAddresses();
      toast("Saved address removed.");
    } catch (error) { toast(error.message); }
  });
  $("#menuToggle").addEventListener("click", () => {
    const open = $("#navLinks").classList.toggle("open");
    $("#menuToggle").setAttribute("aria-expanded", String(open));
    $("#menuToggle").setAttribute("aria-label", open ? "Close navigation menu" : "Open navigation menu");
  });
  $$("#navLinks a").forEach(link => link.addEventListener("click", () => {
    $("#navLinks").classList.remove("open");
    $("#menuToggle").setAttribute("aria-expanded", "false");
  }));
  $$(".app-dialog [data-close]").forEach(button => button.addEventListener("click", () => button.closest("dialog").close()));
  $$(".app-dialog").forEach(dialog => dialog.addEventListener("click", event => {
    if (event.target === dialog) dialog.close();
  }));
  $$(".auth-tabs button").forEach(button => button.addEventListener("click", () => selectAuthMode(button.dataset.authMode)));
  $("#foodSearch").addEventListener("input", loadMenu);
  $("#priceFilter").addEventListener("input", loadMenu);
  let lastOrder = null;
  try { lastOrder = JSON.parse(localStorage.getItem("foodie-last-order") || "null"); } catch { lastOrder = null; }
  if (lastOrder) {
    $("#lastOrderOpen").classList.remove("hidden");
  }
}
document.addEventListener("DOMContentLoaded", init);
