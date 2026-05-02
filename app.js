const form = document.getElementById('orderForm');
const ordersList = document.getElementById('ordersList');
const searchInput = document.getElementById('search');
const clearAllBtn = document.getElementById('clearAll');

const STORAGE_KEY = 'ladies_tailoring_orders';

const readOrders = () => JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
const saveOrders = (orders) => localStorage.setItem(STORAGE_KEY, JSON.stringify(orders));

const toOrder = (formData) => ({
  orderId: formData.get('orderId') || document.getElementById('orderId').value,
  customerName: document.getElementById('customerName').value.trim(),
  phone: document.getElementById('phone').value.trim(),
  garmentType: document.getElementById('garmentType').value,
  fabricSource: document.getElementById('fabricSource').value,
  deliveryDate: document.getElementById('deliveryDate').value,
  measurements: {
    bust: document.getElementById('bust').value,
    waist: document.getElementById('waist').value,
    hip: document.getElementById('hip').value,
    shoulder: document.getElementById('shoulder').value,
    sleeveLength: document.getElementById('sleeveLength').value,
    garmentLength: document.getElementById('garmentLength').value,
  },
  notes: document.getElementById('notes').value.trim(),
  createdAt: new Date().toISOString(),
});

function renderOrders(filter = '') {
  const orders = readOrders();
  const q = filter.trim().toLowerCase();
  const filtered = orders.filter((o) =>
    [o.customerName, o.phone, o.orderId].some((v) => v.toLowerCase().includes(q))
  );

  if (!filtered.length) {
    ordersList.innerHTML = '<p class="empty">No matching orders yet.</p>';
    return;
  }

  ordersList.innerHTML = filtered
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    .map(
      (o) => `
      <article class="order">
        <h4>${o.customerName} • ${o.garmentType}</h4>
        <p class="meta"><span><strong>Order:</strong> ${o.orderId}</span><span><strong>Phone:</strong> ${o.phone}</span><span><strong>Delivery:</strong> ${o.deliveryDate}</span></p>
        <p><strong>Measurements:</strong> Bust ${o.measurements.bust}", Waist ${o.measurements.waist}", Hip ${o.measurements.hip}", Shoulder ${o.measurements.shoulder}", Sleeve ${o.measurements.sleeveLength}", Length ${o.measurements.garmentLength}"</p>
        <p><strong>Fabric:</strong> ${o.fabricSource}</p>
        <p><strong>Notes:</strong> ${o.notes || '—'}</p>
        <small>Saved ${new Date(o.createdAt).toLocaleString()}</small>
      </article>
    `
    )
    .join('');
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const formData = new FormData(form);
  const order = toOrder(formData);
  const orders = readOrders();

  if (orders.some((o) => o.orderId.toLowerCase() === order.orderId.toLowerCase())) {
    alert('Order ID already exists. Please use a unique ID.');
    return;
  }

  orders.push(order);
  saveOrders(orders);
  form.reset();
  renderOrders(searchInput.value);
});

searchInput.addEventListener('input', () => renderOrders(searchInput.value));

clearAllBtn.addEventListener('click', () => {
  if (!confirm('Delete all saved orders?')) return;
  saveOrders([]);
  renderOrders(searchInput.value);
});

renderOrders();
