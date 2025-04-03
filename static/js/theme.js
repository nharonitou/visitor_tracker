// static/js/theme.js
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');

    // Ensure themeToggle exists before adding listeners
    if (themeToggle) {
        const body = document.body;
        const switchOn = themeToggle.querySelector('.switch-on');
        const switchOff = themeToggle.querySelector('.switch-off');

        // Function to apply the visual state of the switch and body class
        const applyTheme = (isDarkMode) => {
            body.classList.toggle('dark-mode', isDarkMode);
            body.classList.toggle('light-mode', !isDarkMode);

            // Check if switch elements exist before styling
            if (switchOn && switchOff) {
                if (isDarkMode) {
                    switchOff.style.boxShadow = 'inset 0 1px 3px rgba(0, 0, 0, 0.2)';
                    switchOn.style.boxShadow = 'none';
                } else {
                    switchOn.style.boxShadow = 'inset 0 1px 3px rgba(0, 0, 0, 0.2)';
                    switchOff.style.boxShadow = 'none';
                }
            } else {
                console.warn("Switch 'on' or 'off' elements not found inside #theme-toggle.");
            }
        };

        // Theme toggle functionality
        themeToggle.addEventListener('click', (e) => {
            const rect = themeToggle.getBoundingClientRect();
            // Check if click coordinates are valid
            if (e.clientY === undefined || rect.top === undefined || rect.height === undefined) {
                console.warn("Could not determine click position relative to the switch.");
                // Fallback: just toggle the current state
                const currentIsDark = body.classList.contains('dark-mode');
                applyTheme(!currentIsDark);
                localStorage.setItem('darkMode', !currentIsDark);
                return;
            }

            const clickY = e.clientY - rect.top;
            const isTopHalf = clickY < rect.height / 2;
            let targetIsDarkMode;

            if (isTopHalf) {
                // Clicked top half (ON) -> Light Mode
                targetIsDarkMode = false;
            } else {
                // Clicked bottom half (OFF) -> Dark Mode
                targetIsDarkMode = true;
            }

            applyTheme(targetIsDarkMode);
            localStorage.setItem('darkMode', targetIsDarkMode);
        });

        // Check for saved theme preference on load
        const savedDarkMode = localStorage.getItem('darkMode') === 'true';
        applyTheme(savedDarkMode); // Apply saved or default theme

    } else {
        console.warn("Theme toggle element (#theme-toggle) not found.");
    }
});