# Configs

There are many possible configs that can be done on each repository

Default header locations

"flags" : ["no commit", "independent project", "no auto build", "execs only"]
"setup" : {}
"before build" : {}
"after build" : {}
"local path": "SubSystems/UserInterface",
"headers": ["include", "library"],
"API": {},
"dependencies": {
    "https://gitlab.com/p4nth30n/Runtime/Data/grammars/config_grammar":{},
    "https://github.com/Mbed-TLS/mbedtls" : {
        "commit": "1325942c283c8f78e19502a8c189007fb16033ab",
        "configs": {
            "local_path": "Runtime/Data/Crypto",
            "headers": ["include", "library"],
            "flags" : ["no commit", "independent project"],
            "setup" : {
                "disable executables": {
                    "condition to proceed":"true",
                    "command list":[
                        "sed -i 's/option(ENABLE_PROGRAMS \"Build Mbed TLS programs\\.\" ON)/option(ENABLE_PROGRAMS \"Build Mbed TLS programs\\.\" OFF)/' $$REPO_SRC_PATH$$/CMakeLists.txt",
                        "sed -i 's/option(ENABLE_TESTING \"Build Mbed TLS tests\\.\" ON)/option(ENABLE_TESTING \"Build Mbed TLS tests\\.\" OFF)/' $$REPO_SRC_PATH$$/CMakeLists.txt",
                        "pip install jsonschema",
                        "pip install jinja2"
                    ]
                }
            }
        }
    }
}
