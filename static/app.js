let userToken = null;
const backendUrl = "https://balance-gpt-1.onrender.com";

document.getElementById('loginBtn').addEventListener('click', async () => {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const res = await fetch(`${backendUrl}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (data.success) {
        userToken = data.token;
        document.getElementById('authDiv').style.display = 'none';
        document.getElementById('questionDiv').style.display = 'block';
        document.getElementById('uploadDiv').style.display = 'block';
        document.getElementById('plotDiv').style.display = 'block';
        document.getElementById('filterDiv').style.display = 'block';
        await loadCompanies();
        populateYears();
        document.getElementById('response').innerText = "Login successful!";
    } else {
        alert("Login failed: " + (data.error || ""));
    }
});

// ----------------- Signup -----------------
document.getElementById('signupBtn').addEventListener('click', async () => {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const role = document.getElementById('role').value;
    const company_id = document.getElementById('companyId').value || null;

    const res = await fetch(`${backendUrl}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role, company_id })
    });
    const data = await res.json();
    alert(data.success ? "Signup successful! Please login." : "Signup failed: " + (data.error || ""));
});

// ----------------- Load Companies -----------------
async function loadCompanies() {
    const res = await fetch(`${backendUrl}/companies`, {
        headers: { 'Authorization': JSON.stringify(userToken) }
    });
    const companies = await res.json();

    ['companySelectQuestion','companySelectPlot','companySelectFilter'].forEach(id => {
        const select = document.getElementById(id);
        select.innerHTML = '';
        companies.forEach(c => {
            select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
        });
    });
}
function populateYears() {
    const yearFrom = document.getElementById('yearFrom');
    const yearTo = document.getElementById('yearTo');
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= 2000; y--) {
        yearFrom.innerHTML += `<option value="${y}">${y}</option>`;
        yearTo.innerHTML += `<option value="${y}">${y}</option>`;
    }
}
document.getElementById('askBtn').addEventListener('click', async () => {
    const company_id = document.getElementById('companySelectQuestion').value;
    const question = document.getElementById('questionInput').value;

    const res = await fetch(`${backendUrl}/ask`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': JSON.stringify(userToken)
        },
        body: JSON.stringify({ company_id, question })
    });
    const data = await res.json();
    document.getElementById('response').innerText = data.answer || data.error || '';
});

document.getElementById('uploadBtn').addEventListener('click', async () => {
    const fileInput = document.getElementById('pdfFile');
    if (!fileInput.files.length) return alert("Select a PDF first.");

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    const res = await fetch(`${backendUrl}/upload-pdf`, {
        method: 'POST',
        headers: { 'Authorization': JSON.stringify(userToken) },
        body: formData
    });
    const data = await res.json();
    alert(data.success ? "PDF uploaded!" : "Error: " + (data.error || ""));
    await loadCompanies();
});
document.getElementById('plotBtn').addEventListener('click', async () => {
    const companyId = document.getElementById('companySelectPlot').value;
    const res = await fetch(`${backendUrl}/plot/${companyId}`, {
        headers: { 'Authorization': JSON.stringify(userToken) }
    });
    const data = await res.json();
    alert(data.success ? `Plot generated for ${data.company}` : "Error: " + (data.error || ""));
});
document.getElementById('viewBtn').addEventListener('click', async () => {
    const companyId = document.getElementById('companySelectFilter').value;
    const year_from = document.getElementById('yearFrom').value;
    const year_to = document.getElementById('yearTo').value;

    const res = await fetch(`${backendUrl}/balance_sheet_filtered?company_id=${companyId}&year_from=${year_from}&year_to=${year_to}`, {
        headers: { 'Authorization': JSON.stringify(userToken) }
    });
    const data = await res.json();

    const tbody = document.querySelector('#balanceTable tbody');
    tbody.innerHTML = '';
    if (data.balance_sheets.length) {
        data.balance_sheets.forEach(row => {
            tbody.innerHTML += `
                <tr>
                    <td>${row.year}</td>
                    <td>${row.revenue}</td>
                    <td>${row.assets}</td>
                    <td>${row.liabilities}</td>
                    <td>${row.profit}</td>
                </tr>
            `;
        });
    } else {
        tbody.innerHTML = `<tr><td colspan="5">No balance sheet data found for the selected range.</td></tr>`;
    }
});

