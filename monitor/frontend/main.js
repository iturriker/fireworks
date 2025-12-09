async function loadWorkers() {
    try {
        const res = await fetch('/api/get/workers');
        const workers = await res.json();

        const tbody = document.querySelector('#workers-table tbody');
        tbody.innerHTML = '';

        Object.values(workers).forEach(worker => {
            const tr = document.createElement('tr');
            const formattedTime = new Date(worker.timestamp * 1000).toLocaleString();
            tr.innerHTML = `
                <td>${worker.id}</td>
                <td>${worker.name}</td>
                <td>${worker.active}</td>
                <td>${worker.counter}</td>
                <td>${formattedTime}</td>
                <td>
                    <button class="${worker.active ? 'deactivate' : 'activate'}" 
                            onclick="toggleWorker('${worker.id}', ${!worker.active})">
                        ${worker.active ? 'Desactivar' : 'Activar'}
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Error cargando workers:', err);
    }
}

async function toggleWorker(id, active) {
    fetch('/api/send/command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ worker_id: id, active: active })
    })
    .then(() => loadWorkers())
    .catch(console.error);
}

// Cargar la tabla al inicio
loadWorkers();

// Actualizar cada segundo
setInterval(loadWorkers, 1000);