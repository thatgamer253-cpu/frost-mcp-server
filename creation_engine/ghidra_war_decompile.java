// Ghidra Script: WAR-64.exe Crash Hunter (Deep Dive)
// Targets: Lua Stack Overflow, Siege Cam, Network Buffer
// Author: Kinetic Council

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.app.decompiler.*;
import ghidra.program.model.symbol.*;
import java.io.*;

public class ghidra_war_decompile extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputPath = "C:\\Users\\thatg\\Desktop\\Kinetic_Turtle_Package\\war64_crash_decompilation.txt";
        PrintWriter out = new PrintWriter(new FileWriter(outputPath));
        DecompInterface decompose = new DecompInterface();
        decompose.openProgram(currentProgram);

        out.println("=== WAR-64.exe Crash/Perf Function Decompilation ===");
        out.println("Generated: " + new java.util.Date());
        out.println();

        // 1. Target: Lua C Stack Overflow
        // String address from analysis: 00a9b27c "C stack overflow"
        out.println("--- TARGET 1: Lua C Stack Overflow Limit ---");
        Address luaErrAddr = currentProgram.getAddressFactory().getAddress("00a9b27c"); // Should be string address
        Reference[] luaRefs = getReferencesTo(luaErrAddr);
        for (Reference ref : luaRefs) {
            Function f = getFunctionContaining(ref.getFromAddress());
            if (f != null) {
                out.println("Found Usage in Function: " + f.getName() + " @ " + f.getEntryPoint());
                DecompileResults results = decompose.decompileFunction(f, 60, monitor);
                if (results.decompileCompleted()) {
                    out.println(results.getDecompiledFunction().getC());
                } else {
                    out.println("// Decompilation Failed: " + results.getErrorMessage());
                }
            } else {
                out.println("Found Usage @ " + ref.getFromAddress() + " (No Function Detected)");
            }
        }
        out.println();

        // 2. Target: Siege Weapon Control (Crash Vector)
        // String: "GetSiegeWeaponControlData"
        out.println("--- TARGET 2: Siege Weapon Control ---");
        // We look for references to "GetSiegeWeaponControlData" string if address known
        // or searching
        // For simplicity, let's search for the string again to be safe
        Address siegeStringAddr = findString("GetSiegeWeaponControlData");
        if (siegeStringAddr != null) {
            Reference[] siegeRefs = getReferencesTo(siegeStringAddr);
            for (Reference ref : siegeRefs) {
                Function f = getFunctionContaining(ref.getFromAddress());
                if (f != null) {
                    out.println("Found Siege Function: " + f.getName() + " @ " + f.getEntryPoint());
                    DecompileResults results = decompose.decompileFunction(f, 60, monitor);
                    if (results.decompileCompleted()) {
                        out.println(results.getDecompiledFunction().getC());
                    }
                }
            }
        }
        out.println();

        // 3. Target: Network Buffer Overflow
        // String: "Connection exceeded floodbyte limit"
        out.println("--- TARGET 3: Network Flood Limit ---");
        Address floodAddr = findString("Connection exceeded floodbyte limit");
        if (floodAddr != null) {
            Reference[] floodRefs = getReferencesTo(floodAddr);
            for (Reference ref : floodRefs) {
                Function f = getFunctionContaining(ref.getFromAddress());
                if (f != null) {
                    out.println("Found Network Flood Check: " + f.getName() + " @ " + f.getEntryPoint());
                    DecompileResults results = decompose.decompileFunction(f, 60, monitor);
                    if (results.decompileCompleted()) {
                        out.println(results.getDecompiledFunction().getC());
                    }
                }
            }
        }

        out.println("=== DECOMPILATION COMPLETE ===");
        out.close();
        println("Saved to: " + outputPath);
    }

    private Address findString(String pattern) {
        // Simple linear search for string (slow but effective for specific strings)
        DataIterator dataIter = currentProgram.getListing().getDefinedData(true);
        while (dataIter.hasNext()) {
            Data data = dataIter.next();
            if (data.hasStringValue()) {
                String val = data.getDefaultValueRepresentation();
                if (val.contains(pattern)) {
                    return data.getAddress();
                }
            }
        }
        return null;
    }
}
