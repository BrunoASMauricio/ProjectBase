#include <stdio.h>

#include "exampleHeader.hpp"

void vCallExample(){
    printf("Called print with module value = %s\n", $$REPOSITORYNAME$$_define);
}
