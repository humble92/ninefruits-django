<script>
	import { onMount } from 'svelte';

	let user = null;

	onMount(async () => {
		try {
			const response = await fetch('/user/api/user/info/');
			if (response.ok) {
				user = await response.json();
			} else {
				console.error('Failed to fetch user data');
			}
		} catch (error) {
			console.error('Error fetching user data:', error);
		}
	});
</script>

<main>
	{#if user}
		<h1>Welcome, {user.first_name || user.username}!</h1>
		<p>Profile: {user.profile_type}</p>

		<nav>
			<ul>
				<!-- Common Menu -->
				<li><a href="/user/mypage">My Page</a></li>
				<li><a href="/user/logout">Logout</a></li>

				<!-- Professor Menu -->
				{#if user.profile_type_code === 'P'}
					<li><a href="/professor/courses">My Courses</a></li>
					<li><a href="/professor/students">My Students</a></li>
				{/if}

				<!-- Student Menu -->
				{#if user.profile_type_code === 'S'}
					<li><a href="/student/grades">View Grades</a></li>
					<li><a href="/student/courses">Register for Courses</a></li>
				{/if}

				<!-- Staff Menu -->
				{#if user.profile_type_code === 'F'}
					<li><a href="/staff/admin">Admin Panel</a></li>
					<li><a href="/staff/users">Manage Users</a></li>
				{/if}
			</ul>
		</nav>
	{:else}
		<h1>Loading user information...</h1>
	{/if}
</main>

<style>
	main {
		text-align: center;
		padding: 1em;
		margin: 0 auto;
	}
	nav {
		margin-top: 2em;
	}
	ul {
		list-style-type: none;
		padding: 0;
	}
	li {
		margin: 0.5em 0;
	}
	a {
		text-decoration: none;
		color: #007bff;
		font-size: 1.2em;
	}
	a:hover {
		text-decoration: underline;
	}
</style>