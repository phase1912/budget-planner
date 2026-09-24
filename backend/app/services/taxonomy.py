import uuid

from app.domain.categories import UNCATEGORIZED
from app.models.category import Category
from app.repository.category import CategoryRepository


class TaxonomyService:
    """The user's own categories: create, rename, delete (BRD C6, C7)."""

    def __init__(self, categories: CategoryRepository) -> None:
        self.categories = categories

    async def create(self, user_id: uuid.UUID, name: str) -> Category:
        """Add a custom category, usable by hand and by the agent at once (C6).

        Raises DomainError when the name matches, ignoring case, a built-in or
        one of the user's own: two "Groceries" in the picker would be two
        different buckets nobody could tell apart.
        """
        from app.api.errors import DomainError

        if await self.categories.name_taken(user_id, name):
            raise DomainError(f"A category named “{name}” already exists.")
        return await self.categories.create_custom(user_id, name)

    async def rename(self, category_id: uuid.UUID, user_id: uuid.UUID, name: str) -> Category:
        """Rename one of the user's categories; items and rules follow it by id (C6).

        Raises NotFoundError for a built-in or another user's category, and
        DomainError for a name already in use.
        """
        from app.api.errors import DomainError, NotFoundError

        category = await self.categories.get_owned(category_id, user_id)
        if category is None:
            raise NotFoundError("Category not found")
        if await self.categories.name_taken(user_id, name, ignoring=category.id):
            raise DomainError(f"A category named “{name}” already exists.")
        category.name = name
        return category

    async def delete(
        self, category_id: uuid.UUID, user_id: uuid.UUID, move_to_id: uuid.UUID
    ) -> None:
        """Delete one of the user's categories, refiling what was under it (C7).

        Items move to the chosen category and keep their amounts. Correction
        rules move with them, unless the target is Uncategorized: a rule that
        files into "no decision" would only keep sending items to the review queue.

        Raises NotFoundError for a category or target the user cannot see, and
        DomainError when asked to move the items into the category being deleted.
        """
        from app.api.errors import DomainError, NotFoundError

        category = await self.categories.get_owned(category_id, user_id)
        if category is None:
            raise NotFoundError("Category not found")
        if move_to_id == category.id:
            raise DomainError("Choose another category for its items.")
        target = await self.categories.get_available(move_to_id, user_id)
        if target is None:
            raise NotFoundError("Target category not found")

        await self.categories.move_items(user_id, category.id, target.id)
        if target.name == UNCATEGORIZED and target.user_id is None:
            await self.categories.delete_rules(user_id, category.id)
        else:
            await self.categories.move_rules(user_id, category.id, target.id)
        await self.categories.remove(category)
