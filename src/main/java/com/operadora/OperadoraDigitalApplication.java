package com.operadora;

import org.camunda.bpm.spring.boot.starter.annotation.EnableProcessApplication;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Aplicacao Principal - Operadora Digital do Futuro
 * ===================================================
 *
 * Aplicacao Spring Boot com Camunda BPM embarcado.
 *
 * Para executar:
 *   mvn spring-boot:run
 *
 * Endpoints:
 *   - Camunda Cockpit: http://localhost:8080/camunda/app/cockpit
 *   - Camunda Tasklist: http://localhost:8080/camunda/app/tasklist
 *   - API REST: http://localhost:8080/engine-rest
 */
@SpringBootApplication
@EnableProcessApplication
public class OperadoraDigitalApplication {

    public static void main(String[] args) {
        SpringApplication.run(OperadoraDigitalApplication.class, args);
    }
}
