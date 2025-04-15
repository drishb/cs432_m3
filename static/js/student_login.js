document.getElementById('studentLoginForm').addEventListener('submit', async function (e) {
    e.preventDefault();
  
    const memberId = document.getElementById('memberId').value;
    const password = document.getElementById('password').value;
  
    const res = await fetch('/authUser', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ MemberID: memberId, Password: password })
    });
  
    const data = await res.json();
  
    if (res.ok) {
      localStorage.setItem('token', data.token);
      alert('Login successful');
      window.location.href = '/student_dashboard.html';  // or another page
    } else {
      alert(data.error || 'Login failed');
    }
  });
  