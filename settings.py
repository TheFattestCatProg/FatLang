class SettingsSwitch:
    def __init__(self):
        self.safe = Settings()
        self.unsafe = UnsafeSettings()
        self.is_safe = True

    def get_current(self) -> 'Settings':
        if self.is_safe:
            return self.safe
        else:
            return self.unsafe

    def switch_safe(self):
        self.is_safe = True

    def switch_unsafe(self):
        self.is_safe = False

    def curr_is_safe(self) -> bool:
        return self.is_safe

    def curr_is_unsafe(self) -> bool:
        return not self.is_safe

class Settings:
    def __init__(self):
        self.allow_auto_unpack = True  # auto *a
        self.allow_auto_pack = True  # auto &a
        self.allow_pointer_of_pointer = False  # a**
        self.allow_pointer_casts = False  # A* to B*
        self.allow_struct_pointers_using = False
        self.allow_pointer_variables = False  # A* a = ...
        self.allow_creation_uninited_vars = False  # A a;

class UnsafeSettings(Settings):
    def __init__(self):
        super().__init__()
        self.allow_pointer_of_pointer = True
        self.allow_pointer_casts = True
        self.allow_struct_pointers_using = True
        self.allow_pointer_variables = True
        self.allow_creation_uninited_vars = True