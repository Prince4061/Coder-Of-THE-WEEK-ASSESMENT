document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('userForm');
    const tableBody = document.getElementById('userTableBody');
    const statusMessage = document.getElementById('statusMessage');

    // Fetch and render users on load
    fetchUsers();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;
        const role = document.getElementById('role').value;

        const submitBtn = form.querySelector('button');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Adding...';

        try {
            const response = await fetch('/api/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, email, role }),
            });

            const data = await response.json();
            
            if (data.success) {
                statusMessage.textContent = data.message;
                statusMessage.style.color = '#34d399';
                form.reset();
                fetchUsers(); // Refresh the list
                
                setTimeout(() => {
                    statusMessage.textContent = '';
                }, 3000);
            }
        } catch (error) {
            console.error('Error adding user:', error);
            statusMessage.textContent = 'Failed to add user.';
            statusMessage.style.color = '#f87171';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Add User';
        }
    });

    async function fetchUsers() {
        try {
            const response = await fetch('/api/users');
            const users = await response.json();
            renderUsers(users);
        } catch (error) {
            console.error('Error fetching users:', error);
        }
    }

    function renderUsers(users) {
        tableBody.innerHTML = '';
        if (users.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding: 2rem;">No users found. Add one!</td></tr>`;
            return;
        }

        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.ID}</td>
                <td>${user.Name}</td>
                <td>${user.Email}</td>
                <td><span class="tag ${user.Role}">${user.Role}</span></td>
            `;
            tableBody.appendChild(tr);
        });
    }
});
