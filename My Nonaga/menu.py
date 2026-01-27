import pygame

class Button:
    """Represents a clickable button in the menu."""

    def __init__(self, x, y, width, height, text, color=(100, 100, 100), text_color=(255, 255, 255)):
        """Initialize a button.

        Args:
            x: x-coordinate of button
            y: y-coordinate of button
            width: button width
            height: button height
            text: button text
            color: RGB tuple for button color
            text_color: RGB tuple for text color
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def draw(self, screen, font):
        """Draw the button on the screen.

        Args:
            screen: pygame surface to draw on
            font: pygame font object
        """
        # Draw button background
        button_color = tuple(min(c + 30, 255)
                             for c in self.color) if self.hovered else self.color
        pygame.draw.rect(screen, button_color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)  # Draw border

        # Draw button text
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        """Check if button was clicked.

        Args:
            pos: (x, y) mouse position

        Returns:
            True if clicked, False otherwise
        """
        return self.rect.collidepoint(pos)

    def update_hover(self, pos):
        """Update hover state based on mouse position.

        Args:
            pos: (x, y) mouse position
        """
        self.hovered = self.rect.collidepoint(pos)


class Menu:
    """Displays a menu with buttons to start the game."""

    def __init__(self, screen_width=1200, screen_height=800):
        """Initialize the menu.

        Args:
            screen_width: width of the game window
            screen_height: height of the game window
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_option = None

        # Create buttons
        button_width = 200
        button_height = 60
        center_x = screen_width // 2 - button_width // 2

        self.start_button = Button(
            center_x, 250, button_width, button_height, "Start Game", (50, 150, 50))
        self.quit_button = Button(
            center_x, 350, button_width, button_height, "Quit", (150, 50, 50))
        self.buttons = [self.start_button, self.quit_button]

    def handle_events(self):
        """Handle menu events.

        Returns:
            "start" if Start Game is clicked, "quit" if Quit is clicked, None otherwise
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.MOUSEMOTION:
                for button in self.buttons:
                    button.update_hover(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    if self.start_button.is_clicked(event.pos):
                        return "start"
                    elif self.quit_button.is_clicked(event.pos):
                        return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "quit"

        return None

    def render(self, screen):
        """Render the menu to the screen.

        Args:
            screen: pygame surface to render to
        """
        # Clear screen
        screen.fill((255, 255, 255))

        # Draw title
        font_large = pygame.font.Font(None, 72)
        title = font_large.render("Nonaga", True, (0, 0, 0))
        title_rect = title.get_rect(center=(self.screen_width // 2, 100))
        screen.blit(title, title_rect)

        # Draw buttons
        font_regular = pygame.font.Font(None, 36)
        for button in self.buttons:
            button.draw(screen, font_regular)

        pygame.display.flip()

    def run(self):
        """Run the menu loop.

        Returns:
            "start" if player selected Start Game, "quit" if selected Quit
        """
        pygame.init()
        screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height))
        pygame.display.set_caption("Nonaga")
        clock = pygame.time.Clock()

        while True:
            result = self.handle_events()
            if result:
                pygame.quit()
                return result

            self.render(screen)
            clock.tick(60)
