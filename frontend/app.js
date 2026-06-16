/**
 * CloudShelf LMS — Frontend Application Logic
 * Fetches book catalog from Flask API, handles borrow/return actions,
 * and renders the dashboard with toast notifications.
 */

const API_BASE = '';  // Same origin — served by Flask

// ── Color gradients for book cover stripes (by genre) ────────
const GENRE_GRADIENTS = {
    'Software Engineering': 'linear-gradient(135deg, #c49a6c, #a87a4e)',
    'Computer Science':     'linear-gradient(135deg, #5b9bd5, #3a7bc8)',
    'Programming Languages':'linear-gradient(135deg, #a78bfa, #7c3aed)',
    'Career':               'linear-gradient(135deg, #4ade80, #22c55e)',
};
const DEFAULT_GRADIENT = 'linear-gradient(135deg, #64748b, #475569)';

// ── Toast Notifications ──────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ── Status Badge ─────────────────────────────────────────────
function setStatus(state, text) {
    const badge = document.getElementById('status-badge');
    badge.className = `status-badge ${state}`;
    badge.querySelector('.status-text').textContent = text;
}

// ── Render Book Card ─────────────────────────────────────────
function renderBookCard(book) {
    const available = book.available_copies || 0;
    const total = book.total_copies || 0;
    const borrowers = book.borrowers || [];
    const gradient = GENRE_GRADIENTS[book.genre] || DEFAULT_GRADIENT;

    let badgeClass, badgeText;
    if (available === 0)      { badgeClass = 'unavailable'; badgeText = 'Unavailable'; }
    else if (available <= 1)  { badgeClass = 'low';         badgeText = `${available}/${total} left`; }
    else                      { badgeClass = 'available';   badgeText = `${available}/${total} available`; }

    const borrowerChips = borrowers.length > 0
        ? `<div class="borrowers-row">${borrowers.map(b => `<span class="borrower-chip">📖 ${b}</span>`).join('')}</div>`
        : '';

    const card = document.createElement('div');
    card.className = 'book-card';
    card.id = `book-${book.isbn}`;
    card.innerHTML = `
        <div class="book-cover" style="--cover-gradient: ${gradient}"></div>
        <div class="book-body">
            <span class="book-genre">${book.genre || 'General'}</span>
            <h3 class="book-title">${book.title}</h3>
            <p class="book-author">by ${book.author} · ${book.published_year || ''}</p>
            <p class="book-description">${book.description || ''}</p>
            ${borrowerChips}
            <div class="book-footer">
                <span class="availability-badge ${badgeClass}">${badgeText}</span>
                <div class="book-actions">
                    <button class="btn btn-borrow" onclick="borrowBook('${book.isbn}')"
                        ${available === 0 ? 'disabled' : ''}>Borrow</button>
                    <button class="btn btn-return" onclick="returnBook('${book.isbn}')"
                        ${borrowers.length === 0 ? 'disabled' : ''}>Return</button>
                </div>
            </div>
        </div>
    `;
    return card;
}

// ── Fetch & Render Catalog ───────────────────────────────────
async function loadBooks() {
    try {
        const res = await fetch(`${API_BASE}/api/books`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const books = await res.json();

        const grid = document.getElementById('book-grid');
        grid.innerHTML = '';

        if (books.length === 0) {
            grid.innerHTML = '<div class="loading-state"><p>No books in catalog yet.</p></div>';
            return;
        }

        books.forEach(book => grid.appendChild(renderBookCard(book)));

        // Update stats
        const totalBooks = books.length;
        const totalCopies = books.reduce((s, b) => s + (b.available_copies || 0), 0);
        const checkedOut = books.reduce((s, b) => s + ((b.total_copies || 0) - (b.available_copies || 0)), 0);
        document.getElementById('stat-total').textContent = totalBooks;
        document.getElementById('stat-available').textContent = totalCopies;
        document.getElementById('stat-borrowed').textContent = checkedOut;

        setStatus('connected', 'Floci Connected');
    } catch (err) {
        console.error('Failed to load books:', err);
        setStatus('error', 'Connection Error');
        showToast('Failed to connect to API server', 'error');
    }
}

// ── Borrow Book ──────────────────────────────────────────────
async function borrowBook(isbn) {
    const borrower = document.getElementById('borrower-name').value.trim();
    if (!borrower) {
        showToast('Please enter your name in the Library Card field', 'error');
        document.getElementById('borrower-name').focus();
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/borrow`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ isbn, borrower_name: borrower }),
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Borrow failed', 'error');
            return;
        }
        showToast(data.message, 'success');
        await loadBooks();
    } catch (err) {
        showToast('Network error — is the API running?', 'error');
    }
}

// ── Return Book ──────────────────────────────────────────────
async function returnBook(isbn) {
    const borrower = document.getElementById('borrower-name').value.trim();
    if (!borrower) {
        showToast('Please enter your name in the Library Card field', 'error');
        document.getElementById('borrower-name').focus();
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/return`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ isbn, borrower_name: borrower }),
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Return failed', 'error');
            return;
        }
        showToast(data.message, 'success');
        await loadBooks();
    } catch (err) {
        showToast('Network error — is the API running?', 'error');
    }
}

// ── Initialize ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadBooks();
    // Auto-refresh every 15 seconds to reflect worker updates
    setInterval(loadBooks, 15000);
});
