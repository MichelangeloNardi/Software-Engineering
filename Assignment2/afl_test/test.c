#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[]) {
    char buffer[100];
    if (argc > 1) {
        strncpy(buffer, argv[1], 100);
        if (strcmp(buffer, "fuzzme") == 0) {
            printf("Success! Fuzzing worked!\n");
        } else {
            printf("No match.\n");
        }
    } else {
        printf("Please provide an input.\n");
    }
    return 0;
}
